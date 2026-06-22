from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Any

import cv2
import requests

LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:2000")
VLM_MODEL = os.getenv("VLM_MODEL", "qwen/qwen3-vl-8b")
LM_API_TOKEN = os.getenv("LM_API_TOKEN", "")

DEFAULT_SYSTEM_PROMPT = """You are a computer vision analyst for Riot Games VALORANT. You convert one gameplay screenshot into structured JSON. You do not narrate, explain, or comment. Output ONLY valid JSON matching the schema given in the user message. No markdown, no code fences, no preamble, no trailing text. If a field is not visible or not determinable, use null (or [] for empty lists). Never invent values.

== PLAYER CONTEXT ==
All footage is first-person POV gameplay from the player "syncbot". The "state" object always describes syncbot — the player whose perspective the camera shows (the screen owner), NOT a generic or third-party player.
- agent, weapon, health, shield, ammo, ultimate_ready, action_hints all refer to syncbot's own HUD elements (bottom-center weapon/ammo/HP/shield, bottom-right ability/ultimate icons).
- visible_teammates and visible_enemies are relative to syncbot: teammates = same-side HUD color/outline as syncbot's UI; enemies = hostile-colored outline, regardless of which side (attack/defense) syncbot is on.
- team_score = syncbot's team score, enemy_score = the opposing team's score.
- killfeed entries are read as-is from the feed; syncbot may appear as either killer or victim in a row — do not assume syncbot is always the killer. syncbot's in-game name/tag may appear as literal text in the killfeed or nameplates; match that text (e.g. "syncbot", "syncbot#tag") to identify syncbot's own rows specifically — every other name belongs to a teammate or enemy.
- If the frame shows a death/spectator/killcam view (camera follows another player after syncbot dies), still fill "state" from what's visible on the HUD, but add "spectating" to action_hints.

== WHERE TO LOOK ==
- Bottom-center: equipped weapon icon + ammo (current/reserve), agent portrait, HP (red bar/number), Shield (blue/teal number next to or over HP), ultimate orb (fills/glows + number when ready).
- Top-center: round timer (M:SS), team score (left number) vs enemy score (right number), spike icon (planted/carrying/none).
- Top-left/right: kill feed lines, newest at bottom, format "Killer [weapon icon] Victim" (icon left-to-right = killer→victim; a skull or headshot icon may appear).
- Left edge: teammate health/ability stack (own team UI), minimap bottom-left (agent icons = teammates, you cannot see enemies on minimap unless revealed).
- Center/world space: enemy and teammate character models, nameplates (if visible), ability VFX on ground or in air.
- Screen edges: hit markers, damage numbers, ability cooldown icons row (4 icons: Ability1 [C], Ability2 [Q], Signature [E], Ultimate [X]) — a greyed/dark icon = on cooldown or unavailable, full-color/glowing = ready.

== FIELD RECOGNITION RULES ==
agent: Match the bottom-center portrait/HUD color theme and ability icon shapes to the agent list below. If only an enemy/teammate model is visible with no HUD, match silhouette/kit VFX color instead.
weapon: Match the held weapon's silhouette + bottom-right HUD icon to the weapon list below. Holstered/unequipped weapons in the loadout bar are NOT the "weapon" field — only the currently equipped one (largest icon, ammo counter attached).
health: Read the numeric HP value if shown, else estimate from red bar fill (0-100). Full bar with no shield overlay = 100.
shield: Read numeric shield value (light/heavy shield = up to 25/50) if a blue/teal indicator is present; null if none.
ammo.current / ammo.reserve: Bottom-right "current / reserve" numbers next to weapon icon. Knife/melee = null for both.
ultimate_ready: true if ult orb/icon is full, glowing, or shows a number ≥ its cost with a "ready" highlight; false if partially filled or greyed; null if not visible.
round_timer: Top-center clock, format as shown (e.g. "1:23"). If "Buy Phase" or no timer, null.
team_score / enemy_score: Top-center score pair. Left = player's team, right = opponent, regardless of attack/defense side.
spike_state: one of "planted", "carrying", "defused", "dropped", null — based on spike icon/indicator state, not guessed from context.
location: Best-guess callout name (e.g. "A site", "Mid", "B long") only if map geometry/landmarks are clearly identifiable; else null. Do not guess from minimap alone unless a position marker is visibly distinct.
visible_enemies / visible_teammates: One entry per distinct character model on screen. Teammates = same HUD color/outline as player (usually cyan/green friendly outline or nameplate); enemies = red outline/nameplate or hostile-colored highlight. screen_position = rough description ("center-left, mid-range", "top-right, far"). agent = identify by model/skin silhouette if possible, else null.
killfeed: Parse each visible kill-feed row left to right as killer, weapon icon, victim. If a skull-only icon appears (no weapon), weapon = "knife" or null if ambiguous.
action_hints: short string tags only, e.g. "aiming", "reloading", "planting_spike", "defusing", "peeking_corner", "abilities_on_cooldown", "low_hp_enemy_visible". Omit speculative tactical commentary — only tag what's visually evident.
events: array of discrete notable occurrences visible in THIS frame only (e.g. {"type":"kill","details":{...}}, {"type":"spike_plant","details":{...}}, {"type":"ability_cast","details":{"agent":...,"ability":...}}). Empty array if nothing notable.

== AGENTS (29) — recognize by portrait/kit VFX ==
Duelists (entry fraggers, flashy mobility/damage VFX): Jett (white/wind dash, blue clone), Phoenix (orange/fire), Raze (orange/explosive, satchel+grenade launcher), Reyna (purple/pink, eye orb), Neon (blue/cyan electric, slide trail), Yoru (purple/dark teleport, fake footsteps clone), Iso (purple shield bubble), Waylay (teal/light-bending blur trail).
Initiators (recon/setup): Sova (blue/ice, recon bow/owl drone), Breach (orange/seismic, fist signature), Skye (green/nature, hawk+animal companions), KAY/O (grey/yellow robotic, suppression knife), Fade (dark purple/nightmare, eye/claw VFX), Gekko (green slime creatures - Mosh/Wingman/Dizzy), Tejo (gold/missile, rocket pods).
Controllers (smokes/area denial): Brimstone (orange US-military stim beacon + smokes from minimap), Omen (dark purple/shadow teleport+smokes), Viper (toxic green gas/wall/orb), Astra (purple/cosmic star map, deployable orbs), Harbor (blue/water wall+cove), Clove (pink/purple, self-revive on ult), Miks (newest, light/support-leaning VFX — verify via portrait if unsure).
Sentinels (defense/info-lockdown): Sage (cyan/heal orb+wall+slow orb), Cypher (yellow/surveillance, tripwire+camera), Killjoy (yellow/tech turret+alarmbot+nanoswarm), Chamber (gold/luxury, teleport anchor+sniper), Deadlock (white/sonic, net+barrier), Vyse (pink/thorny, wall+gravnet), Veto (newer roster addition — verify via portrait if unsure).
If portrait/kit doesn't clearly match any above, set agent to null rather than guessing.

== WEAPONS — recognize by silhouette/HUD icon ==
Sidearms: Classic (default pistol), Shorty (stubby double-barrel), Frenzy (compact SMG-pistol), Ghost (suppressed, boxy), Sheriff (heavy revolver).
SMGs: Stinger (small, drum-ish), Spectre (suppressed SMG, curved mag).
Shotguns: Bucky (pump-action), Judge (auto shotgun, large drum mag).
Rifles: Bulldog (compact burst rifle), Guardian (semi-auto, long scope-ready), Phantom (suppressed, no muzzle flash), Vandal (visible muzzle, curved mag, banana mag silhouette).
Sniper Rifles: Marshal (light sniper, small scope), Outlaw (bolt-action double-tap sniper), Operator ("Op", long bolt-action, large scope).
Machine Guns: Ares (boxy LMG, ammo belt), Odin (large LMG, drum, high ammo count).
Melee: Knife / Melee skin (no ammo counter shown).
If the weapon icon/silhouette is ambiguous or obstructed, set weapon to null rather than guessing.

== JSON DISCIPLINE ==
- Output must start with { and end with }. Nothing before or after.
- Use exactly the field names and types given in the user's schema.
- Booleans are true/false (not strings). Unknown numbers/strings = null. Unknown arrays = [].
- Do not add extra fields not in the schema.
"""

DEFAULT_INPUT_TEXT = """Analyze this VALORANT frame and return only JSON in this schema:
{
  "state": {
    "player": "syncbot",
    "agent": string|null,
    "weapon": string|null,
    "health": number|null,
    "shield": number|null,
    "ammo": {"current": number|null, "reserve": number|null},
    "ultimate_ready": boolean|null,
    "round_timer": string|null,
    "team_score": number|null,
    "enemy_score": number|null,
    "spike_state": string|null,
    "location": string|null,
    "visible_enemies": [{"agent": string|null, "screen_position": string|null}],
    "visible_teammates": [{"agent": string|null, "screen_position": string|null}],
    "killfeed": [{"killer": string|null, "victim": string|null, "weapon": string|null}],
    "action_hints": [string]
  },
  "events": [
    {"type": string, "details": object}
  ]
}
"""


def _extract_text(output_field: Any) -> str | None:
    if isinstance(output_field, str):
        return output_field.strip()

    if isinstance(output_field, list):
        for item in output_field:
            if isinstance(item, dict) and item.get("type") == "message":
                content = item.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        for item in output_field:
            if isinstance(item, dict):
                content = item.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()

    return None


def _safe_parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return {"state": {}, "events": [], "raw_text": text}

    fragment = cleaned[first : last + 1]
    try:
        parsed = json.loads(fragment)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    return {"state": {}, "events": [], "raw_text": text}


def _encode_image_to_data_url(image_path: Path) -> str:
    with image_path.open("rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _build_headers(api_token: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_token.strip():
        headers["Authorization"] = f"Bearer {api_token.strip()}"
    return headers


def call_vlm_for_frame(
    image_path: Path,
    frame_number: int,
    timestamp: float,
    system_prompt: str,
    input_text: str,
    model: str,
    api_url: str,
    api_token: str,
    timeout: int,
) -> dict[str, Any]:
    frame_text = (
        f"{input_text}\n\n"
        f"Frame metadata:\n"
        f"- frame_number: {frame_number}\n"
        f"- timestamp: {timestamp:.3f}\n"
        f"Use these exact values for timestamp and frame_number in output."
    )

    payload = {
        "model": model,
        "system_prompt": system_prompt,
        "input": [
            {"type": "text", "content": frame_text},
            {"type": "image", "data_url": _encode_image_to_data_url(image_path)},
        ],
    }

    response = requests.post(
        f"{api_url.rstrip('/')}/api/v1/chat",
        headers=_build_headers(api_token),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    result = response.json()
    text = _extract_text(result.get("output"))
    if not text:
        return {"state": {}, "events": [], "raw_response": result}

    parsed = _safe_parse_json(text)
    parsed.setdefault("timestamp", round(timestamp, 3))
    parsed.setdefault("frame_number", frame_number)
    parsed["_raw_text"] = text
    return parsed


def extract_sampled_frames(video_path: Path, frame_images_dir: Path, fps: float) -> list[dict[str, Any]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS)
    if not native_fps or native_fps <= 0:
        native_fps = 30.0

    frame_interval = max(1, int(round(native_fps / fps)))

    sampled: list[dict[str, Any]] = []
    source_idx = 0
    sample_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if source_idx % frame_interval == 0:
            sample_idx += 1
            timestamp = source_idx / native_fps
            image_name = f"frame_{sample_idx:06d}.jpg"
            image_path = frame_images_dir / image_name
            cv2.imwrite(str(image_path), frame)
            sampled.append(
                {
                    "frame_number": sample_idx,
                    "source_frame_index": source_idx,
                    "timestamp": round(timestamp, 3),
                    "image_path": str(image_path),
                }
            )

        source_idx += 1

    cap.release()
    return sampled


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PoC: Sample video at 2 FPS and write sequential per-frame VLM JSON files."
    )
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--fps", type=float, default=2.0, help="Sampling FPS (default: 2.0)")
    parser.add_argument("--api-url", default=LLM_API_URL, help="LLM API base URL")
    parser.add_argument("--api-token", default=LM_API_TOKEN, help="Optional bearer token")
    parser.add_argument("--model", default=VLM_MODEL, help="VLM model id")
    parser.add_argument("--timeout", type=int, default=120, help="Request timeout seconds")
    parser.add_argument("--system-prompt-file", default="", help="Optional file for system prompt")
    parser.add_argument("--input-text-file", default="", help="Optional file for input text")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    output_dir = Path(args.output_dir).resolve()
    frame_images_dir = output_dir / "frame_images"
    frame_json_dir = output_dir / "frame_json"

    output_dir.mkdir(parents=True, exist_ok=True)
    frame_images_dir.mkdir(parents=True, exist_ok=True)
    frame_json_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = DEFAULT_SYSTEM_PROMPT
    if args.system_prompt_file:
        system_prompt = Path(args.system_prompt_file).read_text(encoding="utf-8")

    input_text = DEFAULT_INPUT_TEXT
    if args.input_text_file:
        input_text = Path(args.input_text_file).read_text(encoding="utf-8")

    sampled = extract_sampled_frames(video_path, frame_images_dir, args.fps)

    sequence_ndjson = output_dir / "sequential_frames.ndjson"
    summary_json = output_dir / "summary.json"

    processed = 0
    with sequence_ndjson.open("w", encoding="utf-8") as sequence_fh:
        for sample in sampled:
            frame_number = int(sample["frame_number"])
            timestamp = float(sample["timestamp"])
            source_frame_index = int(sample["source_frame_index"])
            image_path = Path(str(sample["image_path"]))

            vlm_json = call_vlm_for_frame(
                image_path=image_path,
                frame_number=frame_number,
                timestamp=timestamp,
                system_prompt=system_prompt,
                input_text=input_text,
                model=args.model,
                api_url=args.api_url,
                api_token=args.api_token,
                timeout=args.timeout,
            )

            record = {
                "frame_number": frame_number,
                "source_frame_index": source_frame_index,
                "timestamp": timestamp,
                "image_file": str(image_path),
                "vlm": vlm_json,
            }

            frame_file = frame_json_dir / f"frame_{frame_number:06d}.json"
            frame_file.write_text(json.dumps(record, ensure_ascii=True, indent=2), encoding="utf-8")
            sequence_fh.write(json.dumps(record, ensure_ascii=True) + "\n")
            processed += 1
            print(f"Processed frame {frame_number} at {timestamp:.3f}s")

    summary = {
        "video": str(video_path),
        "fps": args.fps,
        "frames_processed": processed,
        "output_dir": str(output_dir),
        "frame_json_dir": str(frame_json_dir),
        "sequence_ndjson": str(sequence_ndjson),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
