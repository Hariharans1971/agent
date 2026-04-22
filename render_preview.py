from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

from altiusnxt_core import DEFAULT_TASKS, ENGINE, KB, TEMPLATES


ROOT = Path(__file__).resolve().parent
WIDTH = 1600
HEIGHT = 1100
SIDEBAR_W = 300


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("C:/Windows/Fonts") / name.replace(".ttf", ".TTF"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


FONT_REG = load_font("segoeui.ttf", 20)
FONT_SMALL = load_font("segoeui.ttf", 16)
FONT_TITLE = load_font("segoeuib.ttf", 34)
FONT_H2 = load_font("segoeuib.ttf", 24)
FONT_H3 = load_font("segoeuib.ttf", 19)
FONT_BOLD = load_font("segoeuib.ttf", 18)


def rounded(draw: ImageDraw.ImageDraw, xy, fill, outline=None, radius=18, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], font, fill, width_chars: int, line_gap: int = 8):
    x, y = xy
    for line in wrap(text, width=width_chars):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def draw_markdown(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width_chars: int, max_lines: int = 26):
    x, y = xy
    lines_written = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            y += 10
            continue
        if line.startswith("## "):
            draw.text((x, y), line[3:], font=FONT_H2, fill="#1d2935")
            y += FONT_H2.size + 10
            lines_written += 1
            continue
        if line.startswith("### "):
            draw.text((x, y), line[4:], font=FONT_H3, fill="#1d2935")
            y += FONT_H3.size + 8
            lines_written += 1
            continue
        if line.startswith("- "):
            wrapped = wrap(line[2:], width=width_chars - 2)
            for idx, part in enumerate(wrapped):
                prefix = "• " if idx == 0 else "  "
                draw.text((x, y), f"{prefix}{part}", font=FONT_SMALL, fill="#33485b")
                y += FONT_SMALL.size + 6
                lines_written += 1
                if lines_written >= max_lines:
                    draw.text((x, y), "...", font=FONT_SMALL, fill="#667789")
                    return y
            continue
        wrapped = wrap(line, width=width_chars)
        for part in wrapped:
            draw.text((x, y), part, font=FONT_SMALL, fill="#33485b")
            y += FONT_SMALL.size + 6
            lines_written += 1
            if lines_written >= max_lines:
                draw.text((x, y), "...", font=FONT_SMALL, fill="#667789")
                return y
    return y


def build_preview(copilot: str, role_label: str, output_path: Path):
    sample_prompt = {
        "marketing": "Create a short campaign brief for product data enrichment.",
        "hr": "Create a first-round interview kit for a B2B content marketing manager.",
    }[copilot]
    result = ENGINE.generate(copilot=copilot, message=sample_prompt, template_id=None, conversation=[])
    templates = [item for item in TEMPLATES if item["team"] == copilot][:4]
    recent_tasks = DEFAULT_TASKS[copilot]
    knowledge = KB.list_documents(user_role="admin")[:3]

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f6f8")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#f4f6f8")
    rounded(draw, (0, 0, SIDEBAR_W, HEIGHT), fill="#112334", radius=0)

    # Sidebar
    draw.rounded_rectangle((28, 32, 86, 90), radius=18, fill="#1d6280")
    draw.text((43, 47), "AN", font=FONT_BOLD, fill="#eef5f7")
    draw.text((105, 36), "Internal Workspace", font=FONT_SMALL, fill="#a7bbc8")
    draw.text((105, 58), "AltiusNxt Team Copilot", font=FONT_BOLD, fill="#eef5f7")

    rounded(draw, (24, 118, 276, 190), fill="#1a3041", outline="#2a4758")
    draw.text((40, 136), "Session", font=FONT_SMALL, fill="#96aab8")
    draw.text((40, 158), "Preview User", font=FONT_BOLD, fill="#eef5f7")
    draw.text((40, 182), f"{role_label} access", font=FONT_SMALL, fill="#c2d1da")

    nav_y = 222
    for label, active in [
        ("Workspace", True),
        ("Templates", False),
        ("Knowledge Base", False),
        ("Saved Drafts", False),
        ("Admin", False),
    ]:
        fill = "#20384a" if active else "#112334"
        outline = "#38566a" if active else None
        rounded(draw, (24, nav_y, 276, nav_y + 44), fill=fill, outline=outline, radius=14)
        draw.text((42, nav_y + 12), label, font=FONT_SMALL, fill="#d9e5ec")
        nav_y += 56

    rounded(draw, (24, 540, 276, 860), fill="#1a3041", outline="#2a4758")
    draw.text((42, 560), "Recent Tasks", font=FONT_BOLD, fill="#eef5f7")
    task_y = 602
    for task in recent_tasks:
        rounded(draw, (40, task_y, 260, task_y + 64), fill="#223949", radius=14)
        draw_wrapped_text(draw, task, (54, task_y + 14), FONT_SMALL, "#d9e5ec", width_chars=24, line_gap=4)
        task_y += 78

    # Main frame
    draw.text((336, 38), "Operational Copilot", font=FONT_SMALL, fill="#667789")
    draw.text((336, 64), f"{copilot.capitalize()} Copilot workspace", font=FONT_TITLE, fill="#1d2935")
    rounded(draw, (1180, 42, 1340, 84), fill="#dbeaf1")
    draw.text((1205, 55), "Local grounded mode", font=FONT_SMALL, fill="#08384c")
    rounded(draw, (1350, 42, 1498, 84), fill="#edf1f4")
    draw.text((1386, 55), f"{role_label}", font=FONT_SMALL, fill="#667789")

    # Team cards
    card_fill_a = "#ffffff"
    card_fill_b = "#ffffff"
    outline_a = "#0d4b66" if copilot == "marketing" else "#d7dde3"
    outline_b = "#0d4b66" if copilot == "hr" else "#d7dde3"
    rounded(draw, (336, 120, 700, 214), fill=card_fill_a, outline=outline_a, radius=18, width=2)
    rounded(draw, (716, 120, 1080, 214), fill=card_fill_b, outline=outline_b, radius=18, width=2)
    draw.text((360, 142), "Marketing", font=FONT_SMALL, fill="#667789")
    draw.text((360, 166), "Marketing Copilot", font=FONT_BOLD, fill="#1d2935")
    draw.text((360, 190), "Campaigns, landing pages, ads, SEO, sales-support content", font=FONT_SMALL, fill="#667789")
    draw.text((740, 142), "HR", font=FONT_SMALL, fill="#667789")
    draw.text((740, 166), "HR Copilot", font=FONT_BOLD, fill="#1d2935")
    draw.text((740, 190), "Job descriptions, resumes, interviews, outreach, onboarding", font=FONT_SMALL, fill="#667789")

    # Template chips
    draw.text((336, 242), "Prompt Templates", font=FONT_BOLD, fill="#1d2935")
    chip_x = 336
    chip_y = 276
    for template in templates:
        label = template["title"]
        w = max(150, int(draw.textlength(label, font=FONT_SMALL) + 38))
        rounded(draw, (chip_x, chip_y, chip_x + w, chip_y + 40), fill="#f8fafb", outline="#d7dde3", radius=20)
        draw.text((chip_x + 18, chip_y + 11), label, font=FONT_SMALL, fill="#1d2935")
        chip_x += w + 12

    # Chat panel
    rounded(draw, (336, 332, 1080, 1028), fill="#ffffff", outline="#d7dde3", radius=22)
    draw.rectangle((336, 332, 1080, 900), fill="#f7fafc")
    rounded(draw, (372, 370, 978, 438), fill="#ffffff", outline="#dce3e8", radius=18)
    draw_markdown(
        draw,
        f"## {copilot.capitalize()} Copilot\n" + (
            "Tell me the service, audience, and asset type you want. I can generate landing pages, ad copy, LinkedIn posts, email drafts, SEO briefs, and campaign summaries."
            if copilot == "marketing"
            else "Tell me the role or hiring task you need. I can draft job descriptions, interview kits, onboarding plans, recruiter emails, and resume summaries."
        ),
        (394, 388),
        width_chars=72,
        max_lines=8,
    )

    rounded(draw, (432, 472, 1028, 560), fill="#0d4b66", radius=18)
    draw_wrapped_text(draw, sample_prompt, (458, 498), FONT_SMALL, "#eef5f7", width_chars=62, line_gap=6)

    rounded(draw, (372, 590, 1028, 860), fill="#ffffff", outline="#dce3e8", radius=18)
    draw_markdown(draw, result["answer"], (394, 610), width_chars=74, max_lines=18)

    rounded(draw, (336, 908, 1080, 1028), fill="#ffffff", outline="#d7dde3", radius=22)
    draw.text((366, 934), "Ask for a landing page, a JD, an interview kit, or paste a resume...", font=FONT_SMALL, fill="#8c9aa8")
    rounded(draw, (874, 958, 1010, 1004), fill="#0d4b66", radius=14)
    draw.text((905, 972), "Run Copilot", font=FONT_SMALL, fill="#f3fbff")

    # Right rail
    rounded(draw, (1112, 120, 1560, 460), fill="#ffffff", outline="#d7dde3", radius=22)
    draw.text((1140, 144), "Source Context", font=FONT_BOLD, fill="#1d2935")
    draw.text((1450, 144), "Grounding", font=FONT_SMALL, fill="#667789")
    source_y = 184
    for source in result["sources"][:3]:
        rounded(draw, (1136, source_y, 1536, source_y + 82), fill="#f8fafb", outline="#d7dde3", radius=16)
        draw.text((1154, source_y + 14), source["title"][:34], font=FONT_BOLD, fill="#1d2935")
        draw.text((1154, source_y + 38), source["category"], font=FONT_SMALL, fill="#667789")
        draw_wrapped_text(draw, source["excerpt"], (1154, source_y + 58), FONT_SMALL, "#667789", width_chars=44, line_gap=4)
        source_y += 96

    rounded(draw, (1112, 482, 1560, 706), fill="#ffffff", outline="#d7dde3", radius=22)
    draw.text((1140, 506), "Output Actions", font=FONT_BOLD, fill="#1d2935")
    action_y = 548
    for label in ["Save Draft", "Copy Latest Output", "Export Markdown"]:
        rounded(draw, (1140, action_y, 1530, action_y + 48), fill="#ffffff", outline="#d7dde3", radius=14)
        draw.text((1162, action_y + 14), label, font=FONT_SMALL, fill="#1d2935")
        action_y += 62
    draw_wrapped_text(draw, "Latest output came from the local grounded path.", (1142, 666), FONT_SMALL, "#667789", width_chars=42, line_gap=4)

    rounded(draw, (1112, 728, 1560, 1028), fill="#ffffff", outline="#d7dde3", radius=22)
    draw.text((1140, 752), "Task History", font=FONT_BOLD, fill="#1d2935")
    hist_y = 794
    for task in recent_tasks:
        rounded(draw, (1140, hist_y, 1530, hist_y + 52), fill="#f8fafb", outline="#d7dde3", radius=14)
        draw_wrapped_text(draw, task, (1158, hist_y + 14), FONT_SMALL, "#33485b", width_chars=42, line_gap=4)
        hist_y += 66

    image.save(output_path)


def build_overview(output_path: Path):
    marketing_path = ROOT / "marketing-preview.png"
    hr_path = ROOT / "hr-preview.png"
    if not marketing_path.exists() or not hr_path.exists():
        build_preview("marketing", "Marketing session", marketing_path)
        build_preview("hr", "HR session", hr_path)

    marketing = Image.open(marketing_path).resize((740, 510))
    hr = Image.open(hr_path).resize((740, 510))

    canvas = Image.new("RGB", (1600, 1220), "#f4f6f8")
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, 1600, 1220), fill="#f4f6f8")
    rounded(draw, (40, 36, 1560, 280), fill="#ffffff", outline="#d7dde3", radius=28)
    rounded(draw, (76, 72, 136, 132), fill="#1d6280", radius=18)
    draw.text((93, 90), "AN", font=FONT_BOLD, fill="#eef5f7")
    draw.text((164, 72), "AltiusNxt Team Copilot", font=FONT_TITLE, fill="#1d2935")
    draw.text((166, 118), "Internal AI workspace for Marketing and HR with company-grounded knowledge, drafts, uploads, and role-based access.", font=FONT_SMALL, fill="#667789")

    rounded(draw, (74, 168, 510, 240), fill="#f8fafb", outline="#d7dde3", radius=20)
    draw.text((96, 190), "Local demo accounts", font=FONT_BOLD, fill="#1d2935")
    draw.text((96, 216), "marketing@altiusnxt.local   |   hr@altiusnxt.local   |   admin@altiusnxt.local", font=FONT_SMALL, fill="#667789")

    rounded(draw, (560, 168, 920, 240), fill="#dbeaf1", radius=20)
    draw.text((586, 190), "Runtime mode", font=FONT_BOLD, fill="#08384c")
    draw.text((586, 216), ENGINE.runtime_mode().replace("_", " "), font=FONT_SMALL, fill="#08384c")

    rounded(draw, (956, 168, 1524, 240), fill="#f8fafb", outline="#d7dde3", radius=20)
    draw.text((982, 190), "Core capabilities", font=FONT_BOLD, fill="#1d2935")
    draw.text((982, 216), "Auth, role protection, drafts, task history, uploads, knowledge notes, and two specialist copilots", font=FONT_SMALL, fill="#667789")

    # Login preview card
    rounded(draw, (40, 318, 420, 1168), fill="#112334", radius=30)
    draw.text((76, 364), "Start Session", font=FONT_SMALL, fill="#a7bbc8")
    draw.text((76, 394), "Enter the AltiusNxt workspace", font=FONT_H2, fill="#eef5f7")
    draw_wrapped_text(
        draw,
        "Sign in with a local demo account to unlock the right copilot workspace. HR content remains restricted to HR or admin sessions.",
        (76, 440),
        FONT_SMALL,
        "#d3e0e7",
        width_chars=32,
        line_gap=6,
    )
    rounded(draw, (76, 552, 384, 608), fill="#ffffff", radius=16)
    draw.text((98, 570), "Email", font=FONT_SMALL, fill="#667789")
    rounded(draw, (76, 632, 384, 688), fill="#ffffff", radius=16)
    draw.text((98, 650), "Password", font=FONT_SMALL, fill="#667789")
    rounded(draw, (76, 720, 384, 778), fill="#1d6280", radius=16)
    draw.text((162, 740), "Open Workspace", font=FONT_SMALL, fill="#eef5f7")

    demo_y = 842
    for role, email in [
        ("Marketing demo", "marketing@altiusnxt.local"),
        ("HR demo", "hr@altiusnxt.local"),
        ("Admin demo", "admin@altiusnxt.local"),
    ]:
        rounded(draw, (76, demo_y, 384, demo_y + 94), fill="#1a3041", outline="#2a4758", radius=18)
        draw.text((96, demo_y + 16), role, font=FONT_BOLD, fill="#eef5f7")
        draw.text((96, demo_y + 48), email, font=FONT_SMALL, fill="#c2d1da")
        demo_y += 112

    # Workspace previews
    draw.text((472, 326), "Marketing Copilot Workspace", font=FONT_H2, fill="#1d2935")
    rounded(draw, (452, 360, 1212, 890), fill="#ffffff", outline="#d7dde3", radius=28)
    canvas.paste(marketing, (462, 370))

    draw.text((472, 918), "HR Copilot Workspace", font=FONT_H2, fill="#1d2935")
    rounded(draw, (452, 952, 1212, 1198), fill="#ffffff", outline="#d7dde3", radius=28)
    # The canvas is shorter than a full second row, so crop the HR image into the available area.
    hr_cropped = hr.crop((0, 0, 740, 228))
    canvas.paste(hr_cropped, (462, 962))

    rounded(draw, (1240, 360, 1560, 1168), fill="#ffffff", outline="#d7dde3", radius=28)
    draw.text((1268, 390), "What this preview shows", font=FONT_BOLD, fill="#1d2935")
    preview_notes = [
        "Login and role-aware access",
        "Marketing workspace with templates, chat, sources, and actions",
        "HR workspace with protected role access",
        "Knowledge base uploads and admin note controls",
        "SQLite-backed drafts and task history",
        "Optional live OpenAI mode when OPENAI_API_KEY is set",
    ]
    note_y = 432
    for note in preview_notes:
        draw_wrapped_text(draw, f"- {note}", (1268, note_y), FONT_SMALL, "#33485b", width_chars=28, line_gap=5)
        note_y += 74

    draw.text((1268, 884), "Run locally", font=FONT_BOLD, fill="#1d2935")
    draw_wrapped_text(draw, "python server.py\nhttp://127.0.0.1:8765", (1268, 920), FONT_SMALL, "#667789", width_chars=26, line_gap=6)

    draw.text((1268, 1010), "Demo accounts", font=FONT_BOLD, fill="#1d2935")
    draw_wrapped_text(
        draw,
        "marketing@altiusnxt.local / Marketing123!\nhr@altiusnxt.local / HR12345!\nadmin@altiusnxt.local / Admin12345!",
        (1268, 1046),
        FONT_SMALL,
        "#667789",
        width_chars=28,
        line_gap=6,
    )

    canvas.save(output_path)


def main():
    build_preview("marketing", "Marketing session", ROOT / "marketing-preview.png")
    build_preview("hr", "HR session", ROOT / "hr-preview.png")
    build_overview(ROOT / "whole-project-preview.png")


if __name__ == "__main__":
    main()
