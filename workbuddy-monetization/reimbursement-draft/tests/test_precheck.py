
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from precheck import read_batch, reconcile, render, run
from package_release import validate_frontmatter
from sources import inspect_file


def native(number, day="2026-10-08", kind="普通发票", buyer="演示单位", total="113.00",
           net="100.00", tax="13.00", rate="0.13", mode=""):
    return f"""<EInvoice xmlns="urn:synthetic"><Header><InherentLabel><GeneralOrSpecialVAT>
    <LabelName>{kind}</LabelName></GeneralOrSpecialVAT></InherentLabel>
    <SpecificBizType><LabelName>{mode}</LabelName></SpecificBizType></Header>
    <EInvoiceData><BuyerInformation><BuyerName>{buyer}</BuyerName><BuyerIdNum>TEST-001</BuyerIdNum>
    </BuyerInformation><SellerInformation><SellerName>演示销售方</SellerName></SellerInformation>
    <BasicInformation><TotalAmWithoutTax>{net}</TotalAmWithoutTax><TotalTaxAm>{tax}</TotalTaxAm>
    <TotalTax-includedAmount>{total}</TotalTax-includedAmount></BasicInformation>
    <IssuItemInformation><ItemName>测试用品</ItemName><Amount>{net}</Amount><TaxRate>{rate}</TaxRate>
    <ComTaxAm>{tax}</ComTaxAm></IssuItemInformation></EInvoiceData>
    <TaxSupervisionInfo><InvoiceNumber>{number}</InvoiceNumber><IssueTime>{day}</IssueTime>
    </TaxSupervisionInfo></EInvoice>"""


def ticket_no(i):
    return "26" + str(i).zfill(18)


class PrecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = {
            "expected_count": 1, "files": [], "buyer": "演示单位", "buyer_id": "TEST-001",
            "period": "2026-10",
            "columns": [{"label": label, "key": key} for label, key in
                        (("开票日期", "date"), ("金额", "total"), ("号码", "number"))],
        }

    def add(self, name, data):
        path = self.base / name
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        self.config["files"].append(name)
        return path

    def batch(self):
        return read_batch(self.config, self.base)

    def report(self):
        return run(self.config, self.base, self.batch())

    def observe(self, ticket, values, confidence=None):
        entry = {}
        for key, value in values.items():
            evidence = f"{key}: {value}" if confidence is None else f"票面 {key} 栏"
            entry[key] = {"value": value, "evidence": evidence}
            if confidence is not None:
                entry[key]["confidence"] = confidence
        self.config.setdefault("observations", {})[ticket["id"]] = {
            "sha256": ticket["sha256"], "fields": entry,
        }

    def test_order_xml_and_stability(self):
        self.add("普票.xml", native(ticket_no(1)))
        results = [render(self.report()) for _ in range(3)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])
        self.assertIn("| 开票日期 | 金额 | 号码 |", results[0])
        self.assertIn("113.00〔S1〕", results[0])
        self.assertIn("**通过**", results[0])
        self.assertEqual(results[0].count("## "), 7)

    def test_mismatch_and_unreadable_only_inventory(self):
        self.add("收到.xml", native(ticket_no(1)))
        self.config["files"].append("未收到.xml")
        self.config["expected_count"] = 2
        report = self.report()
        self.assertEqual(report["actual"], 1)
        self.assertEqual(render(report).count("## "), 1)
        self.assertIn("已中止", render(report))

    def test_missing_reason_on_twenty_invoices(self):
        self.config["expected_count"] = 20
        self.config["columns"].insert(1, {"label": "消费事由", "key": "reason"})
        for i in range(20):
            self.add(f"{i}.xml", native(ticket_no(i)))
        report = self.report()
        self.assertEqual(len(report["rows"]), 20)
        self.assertTrue(all(row["cells"][1]["value"] == "" for row in report["rows"]))
        self.assertEqual(len([p for p in report["pending"] if p[1] == "消费事由"]), 20)
        self.assertEqual(report["totals"]["status"], "未通过")
        self.config["infer_reason"] = True
        self.assertEqual(render(self.report()).count("【推断】测试用品（依据：项目名称）"), 20)

    def test_fifty_batch_duplicates_and_history(self):
        self.config["expected_count"] = 50
        for i in range(50):
            n = i - 5 if 5 <= i < 10 else i
            self.add(f"{i}.xml", native(ticket_no(n), day="2026-10-09" if i == 5 else "2026-10-08"))
        history = self.base / "历史.csv"
        history.write_text("发票号码,报销人,报销日期\n" + "".join(
            f"{ticket_no(i)},测试人,2026-09-10\n" for i in (10, 11, 12)), encoding="utf-8-sig")
        self.config["history"] = history.name
        report = self.report()
        self.assertEqual(len(report["rows"]), 37)
        self.assertEqual(sum("批内重复" in b[2] for b in report["blocks"]), 10)
        self.assertEqual(sum("历史台账" in b[2] for b in report["blocks"]), 3)
        self.assertEqual({b[0] for b in report["blocks"]}, {f"{i + 1}. {i}.xml" for i in range(13)})

    def test_number_gate_variants(self):
        variants = [ticket_no(i)[1:] if i < 4 else "25" + ticket_no(i)[2:] for i in range(8)]
        variants += [ticket_no(8)] * 2
        self.config["expected_count"] = 11
        for i, number in enumerate([*variants, ticket_no(11)]):
            self.add(f"{i}.xml", native(number))
        report = self.report()
        self.assertEqual(len(report["rows"]), 1)
        self.assertEqual([b[1] for b in report["blocks"]], ["号码异常"] * 10)

    def test_buyer_and_period(self):
        self.add("专票.xml", native(ticket_no(4), kind="增值税专用发票", buyer="别的单位", day="2026-09-05"))
        report = self.report()
        self.assertEqual({b[1] for b in report["blocks"]}, {"抬头不符", "期间外"})
        self.assertEqual(report["totals"]["difference"], Decimal("113.00"))

    def test_amount_branches(self):
        self.config["expected_count"] = 15
        bad = [dict(total="113.01"), dict(total="114"), dict(tax="12", total="112"),
               dict(tax="13.02", total="113.02"), dict(tax="0", total="100")]
        for i, params in enumerate(bad):
            self.add(f"{i}.xml", native(ticket_no(i), **params))
        for i in range(5, 15):
            params = dict(rate="免税", tax="***", total="100") if i < 10 else dict(mode="差额征税")
            self.add(f"{i}.xml", native(ticket_no(i), **params))
        report = self.report()
        self.assertEqual({b[0] for b in report["blocks"]}, {f"{i + 1}. {i}.xml" for i in range(5)})
        self.assertTrue(all(b[1] == "勾稽不平" for b in report["blocks"]))
        self.assertEqual(sum("乘算不适用" in p[2] for p in report["pending"]), 5)
        self.assertEqual(len(report["rows"]), 5)

    def test_reconciliation_independent_of_row_generation(self):
        self.add("票.xml", native(ticket_no(1)))
        report = self.report()
        for changed in ("112.99", "113.01", "￥112.99"):
            with self.subTest(changed=changed):
                rows = copy.deepcopy(report["rows"])
                rows[0]["cells"][1]["value"] = changed
                result = reconcile(report["tickets"], rows, report["columns"], [], [])
                self.assertEqual(result["status"], "未通过")
                self.assertEqual(abs(result["difference"]), Decimal("0.01"))

    def test_travel_xml_uses_invoice_number_not_passenger_ticket(self):
        shared = "<NameOfPurchaser>演示单位</NameOfPurchaser><UnifiedSocialCreditCodeOfPurchaser>TEST-001</UnifiedSocialCreditCodeOfPurchaser><ETicketNumber>WRONG</ETicketNumber>"
        rail = f"<xbrl>{shared}<ElectronicInvoiceRailwayETicketNumber>{ticket_no(1)}</ElectronicInvoiceRailwayETicketNumber><DateOfIssue>2026-10-08</DateOfIssue><Fare>109</Fare><TotalAmountExcludingTax>100</TotalAmountExcludingTax><TaxAmount>9</TaxAmount><TaxRate>0.09</TaxRate></xbrl>"
        air = f"<xbrl>{shared}<ElectronicInvoiceAirTransportReceiptNumber>{ticket_no(2)}</ElectronicInvoiceAirTransportReceiptNumber><IssueDate>2026-10-09</IssueDate><Fare>80</Fare><FuelSurcharge>20</FuelSurcharge><VatTaxAmount>9</VatTaxAmount><VatRate>0.09</VatRate><CivilAviationDevelopmentFund>50</CivilAviationDevelopmentFund><OtherTaxes>0</OtherTaxes><TotalAmount>159</TotalAmount></xbrl>"
        self.add("铁路.xml", rail)
        self.add("航空.xml", air)
        self.config["expected_count"] = 2
        report = self.report()
        self.assertEqual(report["totals"]["status"], "通过")
        self.assertEqual(report["totals"]["source_total"], Decimal("268"))
        self.assertNotIn("WRONG", render(report))

    def test_invalid_xml_is_held_for_review(self):
        self.add("禁用实体.xml", '<!DOCTYPE a [<!ENTITY b "value">]><a>&b;</a>')
        report = self.report()
        self.assertFalse(report["rows"])
        self.assertIn("DTD", render(report))

    def test_ofd_text_and_evidence(self):
        stream = io.BytesIO()
        values = self.observed_values()
        content = " ".join(f"{key}: {value}" for key, value in values.items())
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("OFD.xml", "<OFD><DocBody><DocRoot>Doc_0/Document.xml</DocRoot></DocBody></OFD>")
            archive.writestr("Doc_0/Document.xml", '<Document><Pages><Page BaseLoc="Pages/Content.xml"/></Pages></Document>')
            archive.writestr("Doc_0/Pages/Content.xml", f"<Page><TextCode>{content}</TextCode></Page>")
        self.add("文本.ofd", stream.getvalue())
        ticket = self.batch()[0]
        self.assertEqual(ticket["source"], "S2")
        self.observe(ticket, values)
        self.assertEqual(self.report()["totals"]["status"], "通过")
        fields = self.config["observations"]["1"]["fields"]
        fields["number"]["value"] = ticket_no(2)
        self.assertIn("待人工", render(self.report()))
        self.assertFalse(self.report()["rows"])

    def test_pdf_text_and_scan_routing(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        writer = PdfWriter()
        page = writer.add_blank_page(600, 800)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        contents = DecodedStreamObject()
        contents.set_data(b"BT /F1 12 Tf 20 700 Td (number: 26000000000000000001) Tj ET")
        page[NameObject("/Contents")] = contents
        stream = io.BytesIO()
        writer.write(stream)
        path = self.add("文本.pdf", stream.getvalue())
        ticket = inspect_file(path)
        self.assertEqual(ticket["source"], "S2")
        self.assertIn(ticket_no(1), ticket["text"])

        writer = PdfWriter()
        writer.add_blank_page(600, 800)
        stream = io.BytesIO()
        writer.write(stream)
        path = self.add("无文字层.pdf", stream.getvalue())
        self.assertEqual(inspect_file(path)["source"], "S3")

    def observed_values(self):
        return {"number": ticket_no(1), "date": "2026-10-08", "kind": "ordinary",
                "buyer": "演示单位", "buyer_id": "TEST-001", "net": "100",
                "tax": "13", "rate": "13%", "total": "113"}

    def test_image_confidence_and_fingerprint(self):
        image = self.add("照片.jpg", b"\xff\xd8\xffsynthetic")
        ticket = self.batch()[0]
        self.assertEqual(ticket["source"], "S3")
        self.observe(ticket, self.observed_values(), confidence=0.96)
        self.assertIn("96%）〔S3〕", render(self.report()))
        self.config["observations"]["1"]["fields"]["number"]["confidence"] = 0.89
        report = self.report()
        self.assertFalse(report["rows"])
        self.assertIn("票面 number 栏", render(report))
        image.write_bytes(b"\xff\xd8\xffchanged")
        with self.assertRaisesRegex(ValueError, "指纹"):
            self.report()

    def test_paid_asset_display_names(self):
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        fields = validate_frontmatter(content)
        for key in ("display_name", "display_name_en"):
            original = f'{key}: "{fields[key]}"'
            for invalid in ("报销 底稿", "报销（预审）", "Receipt_Check", "Receipt–Check"):
                with self.subTest(key=key, invalid=invalid):
                    with self.assertRaisesRegex(ValueError, key):
                        validate_frontmatter(content.replace(original, f'{key}: "{invalid}"'))
            allowed = content.replace(original, f'{key}: "报销—Draft-1"')
            self.assertEqual(validate_frontmatter(allowed)[key], "报销—Draft-1")

    def test_cli_and_archive_shape(self):
        self.add("样票.xml", native(ticket_no(1)))
        config = self.base / "批次.json"
        config.write_text(json.dumps(self.config, ensure_ascii=False), encoding="utf-8")
        script = ROOT / "scripts" / "precheck.py"
        for action, filename in (("inspect", "检查.json"), ("run", "结果.md")):
            output = self.base / filename
            cmd = [sys.executable, "-X", "utf8", str(script), action, str(config), "--output", str(output)]
            process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
        target = self.base / "安装包.zip"
        process = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts" / "package_release.py"),
                                  "--output", str(target)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        with zipfile.ZipFile(target) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("SKILL.md", archive.namelist())
            self.assertTrue(all(len(Path(name).parts) <= 2 for name in archive.namelist()))
            self.assertNotIn("assets/样票.xml", archive.namelist())


if __name__ == "__main__":
    unittest.main()
