
"""Read ticket material without network calls, macros, or archive extraction."""
import hashlib
import io
import re
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

LIMIT = 20 * 1024 * 1024
KINDS = {
    "航空运输电子客票行程单": "air", "铁路电子客票": "rail",
    "增值税专用发票": "special", "普通发票": "ordinary",
}
FIELDS = {
    "kind": "票种", "number": "发票号码", "date": "开票日期",
    "buyer": "购买方名称", "buyer_id": "购买方税号", "seller": "销售方名称",
    "seller_id": "销售方税号", "item": "项目名称", "net": "不含税金额",
    "tax": "税额", "total": "价税合计", "rate": "税率", "mode": "计税口径",
    "fare": "票价", "fuel": "燃油附加费", "fund": "民航发展基金",
    "other": "其他税费", "travel_date": "乘车或出行日期", "train": "车次",
    "flight": "航班号", "origin": "出发地", "destination": "到达地",
    "remark": "备注", "reason": "消费事由",
}

NATIVE = {
    "number": ("TaxSupervisionInfo/InvoiceNumber", "Header/InvoiceNumber"),
    "kind": ("Header/InherentLabel/GeneralOrSpecialVAT/LabelName",
             "Header/InvoiceType/LabelName", "Header/InvoiceType"),
    "date": ("TaxSupervisionInfo/IssueTime", "EinvoiceData/BasicInformation/IssueTime"),
    "buyer": ("EinvoiceData/BuyerInformation/BuyerName",),
    "buyer_id": ("EinvoiceData/BuyerInformation/BuyerIdNum",),
    "seller": ("EinvoiceData/SellerInformation/SellerName",),
    "seller_id": ("EinvoiceData/SellerInformation/SellerIdNum",),
    "net": ("EinvoiceData/BasicInformation/TotalAmWithoutTax",),
    "tax": ("EinvoiceData/BasicInformation/TotalTaxAm",),
    "total": ("EinvoiceData/BasicInformation/TotalTax-includedAmount",),
    "item": ("EinvoiceData/IssuItemInformation/ItemName",),
    "remark": ("EinvoiceData/BasicInformation/Remark",),
}
TRAVEL = {
    "buyer": ("NameOfPurchaser",), "buyer_id": ("UnifiedSocialCreditCodeOfPurchaser",),
    "seller": ("NameOfSeller", "IssueParty"), "seller_id": ("UnifiedSocialCreditCodeOfSeller",),
    "fare": ("Fare",), "remark": ("Remarks",),
}
RAIL = dict(TRAVEL, number=("ElectronicInvoiceRailwayETicketNumber",), date=("DateOfIssue",),
            total=("Fare",), net=("TotalAmountExcludingTax",), tax=("TaxAmount",),
            rate=("TaxRate",), travel_date=("TravelDate",), train=("TrainNumber",),
            origin=("DepartureStation",), destination=("DestinationStation",))
AIR = dict(TRAVEL, number=("ElectronicInvoiceAirTransportReceiptNumber",), date=("IssueDate",),
           total=("TotalAmount",), tax=("VatTaxAmount",), rate=("VatRate",),
           fund=("CivilAviationDevelopmentFund",), fuel=("FuelSurcharge",), other=("OtherTaxes",))

def xml_root(data):
    if len(data) > LIMIT or re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", data.replace(b"\x00", b""), re.I):
        raise ValueError("XML 超限或含 DTD/实体声明")
    root = ET.fromstring(data)
    for elem in root.iter():
        elem.tag = elem.tag.rsplit("}", 1)[-1]
    return root

def kind_value(value):
    if value in KINDS.values():
        return value
    return next((kind for label, kind in KINDS.items() if label in value), "")

def mapped(root, mapping):
    fields = {}
    for key, paths in mapping.items():
        matches = [(node.text.strip(), path) for path in paths for node in root.findall(path)
                   if node.text and node.text.strip()]
        values = list(dict.fromkeys(value for value, _ in matches))
        if len(values) == 1:
            fields[key] = {"value": values[0], "evidence": matches[0][1]}
        elif values and key == "item":
            fields[key] = {"value": " / ".join(values), "evidence": matches[0][1]}
    return fields

def xml_fields(root):
    if root.tag.lower() == "einvoice":
        for element in root.iter():
            if element.tag in {"EInvoiceData", "EInvoiceType"}:
                element.tag = "Einvoice" + element.tag[8:]
        fields = mapped(root, NATIVE)
        # The native payload can contain multiple invoice lines with distinct rates.
        lines = []
        for node in root.findall("EinvoiceData/IssuItemInformation"):
            lines.append(mapped(node, {"net": ("Amount", "AmountWithoutTax"),
                                       "tax": ("ComTaxAm", "TaxAmount", "TaxAm"), "rate": ("TaxRate",)}))
        rates = {line.get("rate", {}).get("value", "") for line in lines}
        if len(rates) == 1 and "" not in rates:
            fields["rate"] = lines[0]["rate"]
        flags = [e.text.strip() for p in ("Header/SpecificBizType/LabelName",
                 "Header/UndefinedLabel/Label/LabelName",
                 "EinvoiceData/BasicInformation/LevyMethod/LabelName") for e in root.findall(p) if e.text]
        if any("差额" in flag for flag in flags):
            fields["mode"] = {"value": "差额征税", "evidence": "票面业务标签"}
        elif rates and rates <= {"免税", "不征税"}:
            fields["mode"] = {"value": "免税/不征税", "evidence": "各明细税率"}
        return fields, lines
    if root.tag == "xbrl":
        if root.find("ElectronicInvoiceRailwayETicketNumber") is not None:
            kind, mapping = "rail", RAIL
        elif root.find("ElectronicInvoiceAirTransportReceiptNumber") is not None:
            kind, mapping = "air", AIR
        else:
            raise ValueError("入账信息 XBRL 缺少完整购方或票面字段，请提供原始数电发票 XML")
        fields = mapped(root, mapping)
        fields["kind"] = {"value": kind, "evidence": mapping["number"][0]}
        return fields, []
    raise ValueError("未知 XML 票面结构，请提供原始数电票或相应 PDF/OFD")

def ofd_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 1024 or sum(i.file_size for i in entries) > LIMIT:
            raise ValueError("OFD 解包规模超限")
        if "OFD.xml" not in archive.namelist():
            raise ValueError("缺少 OFD.xml")
        body = xml_root(archive.read("OFD.xml"))
        documents = body.findall("DocBody/DocRoot")
        if len(documents) != 1 or not documents[0].text:
            raise ValueError("OFD 需为单份文档")
        doc = PurePosixPath(documents[0].text.strip().lstrip("/"))
        pages = xml_root(archive.read(doc.as_posix())).findall("Pages/Page")
        return "\n".join(" ".join(e.text for e in xml_root(archive.read(
            (doc.parent / page.attrib["BaseLoc"]).as_posix())).iter("TextCode") if e.text)
            for page in pages)

def pdf_text(data):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF 文本层需要 pypdf，请安装包内 requirements.txt") from exc
    from pypdf.errors import PyPdfError
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or len(reader.pages) > 20:
            raise ValueError("PDF 已加密或超过 20 页")
        return "\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
    except PyPdfError as exc:
        raise ValueError("PDF 损坏或版式无法读取") from exc

def inspect_file(path):
    suffix = path.suffix.lower()
    if suffix not in {".xml", ".ofd", ".pdf", ".jpg", ".jpeg", ".png"}:
        raise ValueError("文件格式不在标准版范围")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if not data or len(data) > LIMIT:
        raise ValueError("空文件或单文件超过 20 MiB")
    result = {"sha256": hashlib.sha256(data).hexdigest(), "fields": {}, "lines": [], "text": ""}
    if suffix == ".xml":
        result["source"] = "S1"
        result["fields"], result["lines"] = xml_fields(xml_root(data))
    elif suffix in {".pdf", ".ofd"}:
        result["text"] = (pdf_text if suffix == ".pdf" else ofd_text)(data).strip()
        result["source"] = "S2" if result["text"] else "S3"
    else:
        if not (data.startswith(b"\xff\xd8\xff") if suffix in {".jpg", ".jpeg"}
                else data.startswith(b"\x89PNG\r\n\x1a\n")):
            raise ValueError("图片签名与扩展名不符")
        result["source"] = "S3"
    return result
