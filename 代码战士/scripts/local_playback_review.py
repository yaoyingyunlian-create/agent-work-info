"""Record real-time local video playback with the toolkit Chromium runtime."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def review(video: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            args=["--autoplay-policy=no-user-gesture-required"]
        )
        page = browser.new_page(viewport={"width": 480, "height": 850})
        page.goto(video.as_uri(), wait_until="domcontentloaded")
        page.locator("video").wait_for()
        page.evaluate("""async () => {
            const video = document.querySelector('video');
            video.pause();
            await new Promise((resolve, reject) => {
                video.addEventListener('error', () => reject(video.error?.message), {once:true});
                if (video.readyState >= 2) resolve();
                else video.addEventListener('loadeddata', resolve, {once:true});
            });
            video.currentTime = 0;
            video.muted = true;
            video.controls = false;
            video.style.cssText = 'width: 324px; height: 576px; object-fit: contain;';
            window.reviewStart = performance.now();
            await video.play();
        }""")
        player = page.locator("video")
        samples = []
        while True:
            result = page.evaluate("""() => {
            const video = document.querySelector('video');
            return {elapsed:(performance.now()-window.reviewStart)/1000,
                time:video.currentTime, frames:video.getVideoPlaybackQuality().totalVideoFrames,
                ended:video.ended, duration:video.duration, rate:video.playbackRate,
                error:video.error?.message ?? null};
            }""")
            filename = f"play_{len(samples):03d}_{result['time']:.3f}s.jpg"
            screenshot = player.screenshot(path=output / filename, type="jpeg", quality=85)
            samples.append({
                "time": result["time"],
                "frames": result["frames"],
                "file": filename,
                "sha256": hashlib.sha256(screenshot).hexdigest(),
            })
            if result["ended"] or result["error"] or result["elapsed"] > result["duration"] + 10:
                break
            page.wait_for_timeout(440)
        browser.close()
    result["samples"] = samples
    result["distinct_captures"] = len({sample["sha256"] for sample in samples})
    result["video"] = str(video)
    result["sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
    result["actual_listening"] = False
    (output / "playback.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if (not result["ended"] or result["error"] or result["rate"] != 1
            or result["distinct_captures"] < 4):
        raise SystemExit("Local playback did not complete at normal speed")
    print(json.dumps({k: result[k] for k in (
        "ended", "duration", "elapsed", "frames", "distinct_captures", "sha256"
    )}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    review(args.video.resolve(strict=True), args.output)
