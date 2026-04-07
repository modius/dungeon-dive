#!/usr/bin/env python3
"""
Analyze video content from post summaries and transcripts to build a taxonomy.

Reads archive/posts/ summaries and video_index.json to extract:
- Games mentioned (primary subject + cross-references)
- Content format tags (review, let's play, unboxing, etc.)
- Mechanic tags (dungeon-crawler, deck-builder, etc.)
- Theme tags (fantasy, sci-fi, horror, etc.)
- Player mode tags (solo, cooperative, competitive)
- Platform tags (tabletop, digital)
- Meta tags (crowdfund, top-10, house-rules, etc.)
- Publishers/designers mentioned

Outputs transcript_analytics.json with per-video tags and aggregate stats.

Usage:
    python3 scripts/analyze_content.py --index video_index.json
    python3 scripts/analyze_content.py --index video_index.json --dry-run
    python3 scripts/analyze_content.py --index video_index.json --reanalyze
"""

import argparse
import json
import os
import re
from collections import Counter, defaultdict


# ── Tag taxonomy ───────────────────────────────────────────────────

# Content format: what kind of video is this?
FORMAT_PATTERNS = {
    "review": [
        r"\breview\b", r"\breviewed\b", r"\bverdict\b",
        r"\brecommend(?:s|ation)?\b", r"\bpros and cons\b",
        r"\bloves? and (?:dislikes?|frustrations?)\b",
    ],
    "overview": [
        r"\boverview\b", r"\btake a look\b", r"\bbrief look\b",
        r"\bquick look\b", r"\bfirst look\b", r"\bcheck(?:ing)? out\b",
    ],
    "lets-play": [
        r"\blet'?s play\b", r"\bplaythrough\b", r"\bplay[\s-]?through\b",
        r"\bcampaign play\b", r"\bsession\b",
    ],
    "unboxing": [
        r"\bunboxing\b", r"\bunbox\b", r"\bwhat'?s in the box\b",
        r"\bcomponents?\b.*\blook\b",
    ],
    "deep-dive": [
        r"\bdeep dive\b", r"\bexhaustive\b", r"\bcomprehensive\b",
        r"\bin[- ]depth\b",
    ],
    "comparison": [
        r"\bvs\.?\s+\w", r"\bversus\b", r"\bcompar(?:e|ison|ing)\b",
        r"\bbetter than\b",
    ],
    "top-list": [
        r"\btop \d+\b(?=.*\b(?:list|games?|picks?|ranking)\b)",
        r"\branking\b", r"\bcurated list\b",
    ],
    "crowdfund-preview": [
        r"\bcrowdfund\b", r"\bkickstarter\b", r"\bgamefound\b",
        r"\bbacking\b", r"\bpledge\b", r"\bpreview\b.*\bcrowdfund\b",
        r"\bcrowdfund\b.*\bpreview\b", r"\bprototype\b",
    ],
    "tutorial": [
        r"\bhow to play\b", r"\bbeginner'?s guide\b", r"\btutorial\b",
        r"\bguide to\b", r"\btips?\b.*\bsurvival\b",
    ],
    "discussion": [
        r"\bdiscussion\b", r"\bthoughts on\b", r"\blet'?s talk\b",
        r"\bcasual discussion\b", r"\bboard game burnout\b",
    ],
    "digital-dive": [
        r"\bdigital dive\b", r"\bvideo game\b", r"\bpc game\b",
        r"\broguelit?e\b", r"\bauto[- ]?battler\b",
    ],
    "buyers-guide": [
        r"\bbuyer'?s guide\b", r"\bcollecting\b", r"\bcollector\b",
    ],
}

# Game mechanics/genre
MECHANIC_PATTERNS = {
    "dungeon-crawler": [
        r"\bdungeon[- ]?crawl(?:er|ing)?\b", r"\bcrawl through\b",
        r"\bdungeon\b.*\bexplor(?:e|ation|ing)\b",
    ],
    "deck-builder": [
        r"\bdeck[- ]?build(?:er|ing)?\b", r"\bcard draft\b",
    ],
    "dice-game": [
        r"\bdice[- ]?(?:game|placement|puzzle|rolling)\b",
        r"\broll and write\b", r"\bpush your luck\b",
    ],
    "hex-crawl": [
        r"\bhex[- ]?crawl\b", r"\bhex[- ]?explor(?:e|ation)\b",
        r"\bhexplor\b",
    ],
    "rpg": [
        r"\brole[- ]?play(?:ing)?\b", r"\brpg\b", r"\bcharacter (?:creation|sheet)\b",
        r"\bleveling up\b", r"\bexperience points\b",
    ],
    "campaign": [
        r"\bcampaign\b", r"\blegacy\b", r"\bmulti[- ]?session\b",
        r"\bprogression\b", r"\bsave state\b",
    ],
    "miniatures": [
        r"\bminiatures?\b", r"\bminis?\b", r"\bpainted\b",
        r"\bmodels?\b.*\bassembl\b",
    ],
    "card-game": [
        r"\bcard game\b", r"\bhand management\b",
    ],
    "tile-laying": [
        r"\btile[- ]?lay(?:ing)?\b", r"\bmodular board\b",
        r"\btiles?\b.*\bexplor\b",
    ],
    "press-your-luck": [
        r"\bpress your luck\b", r"\bpush your luck\b",
        r"\brisk[- ]?reward\b",
    ],
    "sandbox": [
        r"\bsandbox\b", r"\bopen[- ]?world\b", r"\bnon[- ]?linear\b",
    ],
    "tower-defense": [
        r"\btower[- ]?defen[sc]e\b",
    ],
    "wargame": [
        r"\bwargame\b", r"\bwar game\b", r"\bskirmish\b",
    ],
}

# Theme/setting
THEME_PATTERNS = {
    "fantasy": [
        r"\bfantasy\b", r"\bsword and sorcery\b", r"\bmediev(?:al|il)\b",
        r"\bdwarf\b", r"\belves?\b", r"\bgoblin\b", r"\bork\b|\borc\b",
        r"\bdragon\b", r"\bwizard\b", r"\bwarrior\b",
    ],
    "sci-fi": [
        r"\bsci[- ]?fi\b", r"\bscience fiction\b",
        r"\bcyberpunk\b", r"\bfuturistic\b", r"\bgalactic\b",
        r"\bspace (?:hulk|marine|station)\b",
    ],
    "horror": [
        r"\bhorror\b", r"\bcthulhu\b", r"\bgothic\b", r"\blovecraft\b",
        r"\bundead\b", r"\bzombie\b", r"\bvampire\b",
    ],
    "western": [
        r"\bwestern\b", r"\bcowboy\b", r"\bfrontier\b", r"\bwild west\b",
    ],
    "post-apocalyptic": [
        r"\bpost[- ]?apocalyptic\b", r"\bwasteland\b", r"\bradiat\b",
    ],
    "mythology": [
        r"\bmytholog\b", r"\barthurian\b", r"\bnorse\b", r"\bceltic\b",
    ],
    "steampunk": [
        r"\bsteampunk\b",
    ],
    "pirate": [
        r"\bpirate\b", r"\bsailing\b", r"\bocean\b.*\badventure\b",
    ],
}

# Player mode
MODE_PATTERNS = {
    "solo": [
        r"\bsolo\b", r"\bsingle[- ]?player\b", r"\bsolitaire\b",
        r"\bplaying alone\b", r"\bone[- ]?player\b",
    ],
    "cooperative": [
        r"\bcoop\b", r"\bco[- ]?op\b", r"\bcooperativ\b",
        r"\bworking together\b", r"\bteamwork\b",
    ],
    "competitive": [
        r"\bcompetitiv\b", r"\bversus\b", r"\bpvp\b",
        r"\bplayer vs\b",
    ],
    "two-player": [
        r"\btwo[- ]?player\b", r"\b2[- ]?player\b",
    ],
}

# Platform
PLATFORM_PATTERNS = {
    "tabletop": [
        r"\bboard game\b", r"\btabletop\b", r"\bcard game\b",
        r"\btable\b.*\bgame\b",
    ],
    "digital": [
        r"\bdigital\b", r"\bvideo game\b", r"\bpc\b", r"\bsteam\b",
        r"\bconsole\b", r"\bplaystation\b", r"\bnintendo\b",
        r"\broguelit?e\b", r"\bapp\b",
    ],
    "print-and-play": [
        r"\bprint[- ]?and[- ]?play\b", r"\bpnp\b",
    ],
}

# Era tags (when the game was made)
ERA_PATTERNS = {
    "classic": [
        r"\bclassic\b", r"\bvintage\b", r"\bretro\b",
        r"\b(?:19[789]\d|200[0-5])\b.*\b(?:release|edition|original)\b",
    ],
    "modern": [
        r"\bmodern\b.*\bgame\b", r"\bnew release\b",
    ],
}

# Known games list — built from titles, post bodies, and common references.
# This gets expanded by the analysis itself.
KNOWN_GAMES = [
    "Warhammer Quest", "HeroQuest", "Advanced HeroQuest", "Talisman",
    "Shadows of Brimstone", "Four Against Darkness", "Dungeon Degenerates",
    "HEXplore It", "Mork Borg", "Arkham Horror", "Gloomhaven",
    "Descent", "Massive Darkness", "Cthulhu: Death May Die",
    "Runebound", "Gathering Gloom", "Scarlet Heroes",
    "Blackstone Fortress", "Silver Tower", "Cursed City",
    "Folklore: The Affliction", "Altar Quest", "Dungeons & Dragons",
    "Space Hulk", "Doom Pilgrim", "Dungeon Degenerates: The Hand of Doom",
    "Vantage", "Rove", "Fallen Land", "Witcher Adventure Game",
    "Restless", "Legendary", "Hellbringer", "Crypt Crawler Quest",
    "Ball X Pit", "Elder Space", "Void Realm", "Stalagbite",
    "Downcrawl", "Grimscar", "He is Coming", "Dice Commandos",
    "7th Continent", "7th Citadel", "Arydia", "Firefly: The Game",
    "Battle Masters", "Dungenerator", "Sol Cesto", "Valpiedra",
    "Dark Venture", "LA-1", "The Restless", "X-ODUS",
    "Machine Gods", "ZomBN1", "Dragons Down", "Story of Many",
    "League of Dungeoneers", "Pauper's Ladder",
]


def compile_patterns(pattern_dict):
    """Compile regex patterns for efficiency."""
    compiled = {}
    for tag, patterns in pattern_dict.items():
        compiled[tag] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return compiled


FORMAT_RE = compile_patterns(FORMAT_PATTERNS)
MECHANIC_RE = compile_patterns(MECHANIC_PATTERNS)
THEME_RE = compile_patterns(THEME_PATTERNS)
MODE_RE = compile_patterns(MODE_PATTERNS)
PLATFORM_RE = compile_patterns(PLATFORM_PATTERNS)
ERA_RE = compile_patterns(ERA_PATTERNS)


def match_tags(text, compiled_patterns):
    """Return set of tags that match in text."""
    tags = set()
    for tag, regexes in compiled_patterns.items():
        for rx in regexes:
            if rx.search(text):
                tags.add(tag)
                break
    return tags


def extract_games_from_title(title):
    """Extract game name from video title heuristics."""
    games = set()

    # Direct match against known games
    title_lower = title.lower()
    for game in KNOWN_GAMES:
        if game.lower() in title_lower:
            games.add(game)

    # Pattern: "GAME - Review" or "GAME - Take a Look" etc.
    m = re.match(r"^(.+?)(?:\s*[-–—]\s*(?:Review|Overview|Take a Look|Part \d|A |The |Let'?s))", title)
    if m:
        candidate = m.group(1).strip()
        # Don't add very generic titles
        if len(candidate) > 2 and candidate.lower() not in ("the", "a", "an"):
            games.add(candidate)

    return games


def extract_games_from_text(text, title_games):
    """Find game mentions in text, prioritizing known games."""
    games = set()
    text_lower = text.lower()

    for game in KNOWN_GAMES:
        if game.lower() in text_lower:
            games.add(game)

    # Include title-extracted games
    games.update(title_games)

    return games


def analyze_video(video, post_body, transcript_text=None):
    """Analyze a single video and return tag structure."""
    title = video.get("title", "")
    # Combine title + post body + transcript for analysis
    text = "{}\n{}\n{}".format(title, post_body or "", transcript_text or "")

    title_games = extract_games_from_title(title)
    all_games = extract_games_from_text(text, title_games)

    # Primary game = first game from title, or largest set
    primary_game = None
    if title_games:
        primary_game = sorted(title_games, key=len, reverse=True)[0]
    elif all_games:
        primary_game = sorted(all_games, key=len, reverse=True)[0]

    result = {
        "video_id": video["video_id"],
        "title": title,
        "published_at": video.get("published_at", "")[:10],
        "primary_game": primary_game,
        "games": sorted(all_games),
        "format": sorted(match_tags(text, FORMAT_RE)),
        "mechanics": sorted(match_tags(text, MECHANIC_RE)),
        "themes": sorted(match_tags(text, THEME_RE)),
        "player_modes": sorted(match_tags(text, MODE_RE)),
        "platforms": sorted(match_tags(text, PLATFORM_RE)),
        "era": sorted(match_tags(text, ERA_RE)),
    }

    # Build flat tag list for tag cloud
    all_tags = set()
    all_tags.update(result["format"])
    all_tags.update(result["mechanics"])
    all_tags.update(result["themes"])
    all_tags.update(result["player_modes"])
    all_tags.update(result["platforms"])
    all_tags.update(result["era"])
    result["all_tags"] = sorted(all_tags)

    return result


def build_aggregates(analyzed_videos):
    """Build aggregate statistics from per-video analysis."""
    game_counts = Counter()
    primary_game_counts = Counter()
    format_counts = Counter()
    mechanic_counts = Counter()
    theme_counts = Counter()
    mode_counts = Counter()
    platform_counts = Counter()
    era_counts = Counter()
    tag_counts = Counter()
    games_by_year = defaultdict(Counter)
    format_by_year = defaultdict(Counter)

    for v in analyzed_videos:
        year = v["published_at"][:4]

        for g in v["games"]:
            game_counts[g] += 1
            games_by_year[year][g] += 1

        if v["primary_game"]:
            primary_game_counts[v["primary_game"]] += 1

        for f in v["format"]:
            format_counts[f] += 1
            format_by_year[year][f] += 1

        for m in v["mechanics"]:
            mechanic_counts[m] += 1

        for t in v["themes"]:
            theme_counts[t] += 1

        for m in v["player_modes"]:
            mode_counts[m] += 1

        for p in v["platforms"]:
            platform_counts[p] += 1

        for e in v["era"]:
            era_counts[e] += 1

        for t in v["all_tags"]:
            tag_counts[t] += 1

    return {
        "games": game_counts.most_common(50),
        "primary_games": primary_game_counts.most_common(50),
        "formats": format_counts.most_common(),
        "mechanics": mechanic_counts.most_common(),
        "themes": theme_counts.most_common(),
        "player_modes": mode_counts.most_common(),
        "platforms": platform_counts.most_common(),
        "eras": era_counts.most_common(),
        "tag_cloud": tag_counts.most_common(80),
        "games_by_year": {
            y: dict(c.most_common(20)) for y, c in sorted(games_by_year.items())
        },
        "format_by_year": {
            y: dict(c.most_common()) for y, c in sorted(format_by_year.items())
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze video content for taxonomy tags")
    parser.add_argument("--index", default="video_index.json")
    parser.add_argument("--posts-dir", default="archive/posts")
    parser.add_argument("--transcripts-dir", default="archive/transcripts")
    parser.add_argument("--output", default="transcript_analytics.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reanalyze", action="store_true",
                        help="Reanalyze all videos, not just new ones")
    args = parser.parse_args()

    with open(args.index) as f:
        index_data = json.load(f)
    videos = index_data.get("videos", [])
    imported = [v for v in videos if v.get("status") == "imported"]

    # Load existing analytics if not reanalyzing
    existing = {}
    if not args.reanalyze and os.path.exists(args.output):
        with open(args.output) as f:
            old_data = json.load(f)
        for v in old_data.get("videos", []):
            existing[v["video_id"]] = v

    analyzed = []
    new_count = 0
    for video in imported:
        vid = video["video_id"]

        # Skip already analyzed unless reanalyzing
        if vid in existing and not args.reanalyze:
            analyzed.append(existing[vid])
            continue

        # Load post body
        post_path = os.path.join(args.posts_dir, "{}_post.json".format(vid))
        post_body = ""
        if os.path.exists(post_path):
            with open(post_path) as f:
                try:
                    post_data = json.load(f)
                    post_body = post_data.get("body", "")
                except json.JSONDecodeError:
                    pass

        # Load transcript if available
        tx_path = os.path.join(args.transcripts_dir, "{}_transcript.txt".format(vid))
        transcript = ""
        if os.path.exists(tx_path):
            with open(tx_path) as f:
                transcript = f.read()

        result = analyze_video(video, post_body, transcript)
        analyzed.append(result)
        new_count += 1

    # Build aggregates
    aggregates = build_aggregates(analyzed)

    output = {
        "total_analyzed": len(analyzed),
        "last_run": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "aggregates": aggregates,
        "videos": sorted(analyzed, key=lambda v: v["published_at"], reverse=True),
    }

    print("Analyzed {} videos ({} new, {} cached)".format(
        len(analyzed), new_count, len(analyzed) - new_count
    ))
    print("Top games: {}".format(
        ", ".join("{} ({})".format(g, c) for g, c in aggregates["games"][:10])
    ))
    print("Formats: {}".format(
        ", ".join("{} ({})".format(f, c) for f, c in aggregates["formats"])
    ))
    print("Mechanics: {}".format(
        ", ".join("{} ({})".format(m, c) for m, c in aggregates["mechanics"][:10])
    ))
    print("Themes: {}".format(
        ", ".join("{} ({})".format(t, c) for t, c in aggregates["themes"])
    ))
    print("Player modes: {}".format(
        ", ".join("{} ({})".format(m, c) for m, c in aggregates["player_modes"])
    ))
    print("Tag cloud ({} unique tags): {}".format(
        len(aggregates["tag_cloud"]),
        ", ".join(t for t, _ in aggregates["tag_cloud"][:20])
    ))

    if args.dry_run:
        print("\nDRY RUN — not writing output.")
        return

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print("\nWritten to: {}".format(args.output))


if __name__ == "__main__":
    main()
