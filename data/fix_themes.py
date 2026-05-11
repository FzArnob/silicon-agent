"""
Rewrites the Theme column in config.csv to remove all copyright/IP references.
Preserves the visual aesthetic while replacing specific brand/franchise names
with generic descriptions.
"""

import csv
import re
import io

INPUT_FILE = "config.csv"
OUTPUT_FILE = "config.csv"

# ---------------------------------------------------------------------------
# Ordered replacement pairs — (exact_text_to_find, replacement)
# Longer / more specific phrases must come BEFORE shorter partial ones.
# ---------------------------------------------------------------------------
REPLACEMENTS = [

    # ── STAR WARS ────────────────────────────────────────────────────────────
    ("Star Wars Galactic Empire themed command center with Imperial gray and black aesthetics - Star Destroyer desk lamp - Death Star RGB orb - holographic starfield wall projection",
     "Space empire command center with imperial gray and obsidian black aesthetics - interstellar cruiser desk lamp - orbital battle station RGB orb - holographic starfield wall projection"),

    ("Emperor's Sith throne room on Death Star II with deep crimson red and imperial black - Force lightning LED effects - dark side unlimited power station - everything is proceeding as planned",
     "Dark emperor's throne room with deep crimson red and imperial black - crackling energy lightning LED effects - supreme power gaming station"),

    ("Jedi Temple academy library with serene cream white and soft gold lightsaber glow - holocron desk lamp - peaceful Force meditation corner - do or do not there is no try",
     "Ancient temple academy library with serene cream white and soft gold energy blade glow - glowing orb desk lamp - peaceful meditation corner - patience and wisdom gaming station"),

    ("Republic Clone Wars tactical command center with clean trooper white and 501st blue/212th orange accents - holographic battle map display - for the Republic gaming station",
     "Space military tactical command center with clean trooper white and blue/orange accents - holographic battle map display - honor and duty gaming station"),

    ("Mandalorian bounty hunter's ship cockpit with beskar silver and dark green accents - helmet display stand - carbonite freezing chamber LED panel - this is the way",
     "Bounty hunter's ship cockpit with battle-forged silver and dark green accents - helmet display stand - stasis chamber LED panel - warrior code gaming station"),

    ("Mandalorian beskar forge with hammered silver steel and Mandalore blue accents - armorer's workbench aesthetic - this is the Way LED sign - warrior clan forge station",
     "Warrior armorer's forge with hammered silver steel and deep blue accents - armorer's workbench aesthetic - warrior code LED sign - clan forge station"),

    ("Kylo Ren's First Order command shuttle with unstable crossguard red saber crackling on matte black - cracked helmet display - let the past die LED art - conflicted dark side gaming",
     "Dark heir's command vessel with unstable crossguard energy blade crackling on matte black - cracked helmet display - conflicted inner struggle LED art - dark warrior gaming"),

    ("Star Wars droid repair workshop with clean protocol white and astromech blue/gold accents - holographic schematic displays - droid motivator tools desk set - these aren't the droids you're looking for",
     "Sci-fi droid repair workshop with clean white and blue/gold accents - holographic schematic displays - repair tool desk set - mechanoid engineering aesthetic"),

    ("Jedi Temple-inspired luxury battlestation with blue-white cosmic lighting - Massive OLED ultrawide command center design - Premium white showcase hardware with floating shelf décor - Star Wars collector environment optimized for streaming",
     "Ancient temple-inspired luxury battlestation with blue-white cosmic lighting - Massive OLED ultrawide command center design - Premium white showcase hardware with floating shelf décor - sci-fi collector environment optimized for streaming"),

    ("Clone Wars-inspired battlestation with blue-white military RGB - OLED sci-fi immersion with futuristic command-center styling - White hardware accented with tactical blue lighting - Star Wars collector environment designed for streamers",
     "Space military battlestation with blue-white military RGB - OLED sci-fi immersion with futuristic command-center styling - White hardware accented with tactical blue lighting - sci-fi collector environment designed for streamers"),

    ("Rebel Alliance-inspired gaming setup with blue hyperspace RGB - OLED ultrawide immersion with sci-fi starship atmosphere - Dark metallic styling mixed with glowing space décor - Premium streaming-ready Star Wars collector battlestation",
     "Space rebel-inspired gaming setup with blue hyperspace RGB - OLED ultrawide immersion with sci-fi starship atmosphere - Dark metallic styling mixed with glowing space décor - Premium streaming-ready sci-fi collector battlestation"),

    ("Imperial white-themed gaming room with icy blue RGB - Symmetrical dual-monitor setup with floating shelves - Star Wars collectible showcase integrated into desk wall - Luxury white hardware and silent airflow configuration",
     "Pristine white-themed gaming room with icy blue RGB - Symmetrical dual-monitor setup with floating shelves - Sci-fi collectible showcase integrated into desk wall - Luxury white hardware and silent airflow configuration"),

    ("Space western-inspired gaming setup with deep blue lighting - Sci-fi command center atmosphere with holographic RGB - Display shelves packed with Star Wars collectibles - High-end multitasking environment for gaming and streaming",
     "Space western-inspired gaming setup with deep blue lighting - Sci-fi command center atmosphere with holographic RGB - Display shelves packed with sci-fi space collectibles - High-end multitasking environment for gaming and streaming"),

    ("- Sith Empire-inspired battlestation with crimson sci-fi lighting",
     "- Dark space empire-inspired battlestation with crimson sci-fi lighting"),

    ("- Sith-inspired command center with dark crimson RGB",
     "- Dark warrior command center with dark crimson RGB"),

    ("- Sith throne-inspired battlestation with crimson sci-fi RGB",
     "- Dark emperor throne-inspired battlestation with crimson sci-fi RGB"),

    ("- Galactic Empire-inspired battlestation with crimson sci-fi RGB",
     "- Space empire-inspired battlestation with crimson sci-fi RGB"),

    ("- Galactic Empire-inspired battlestation with crimson sci-fi lighting",
     "- Space empire-inspired battlestation with crimson sci-fi lighting"),

    ("- Imperial Empire-inspired battlestation with crimson sci-fi lighting",
     "- Space empire-inspired battlestation with crimson sci-fi lighting"),

    ("Display shelves packed with Star Wars collectibles", "Display shelves packed with sci-fi space collectibles"),
    ("Star Wars collector environment", "sci-fi space collector environment"),
    ("Star Wars collectible showcase", "sci-fi space collectible showcase"),
    ("Star Wars-inspired collector shelving and ambient lighting", "sci-fi space-inspired collector shelving and ambient lighting"),

    # ── TRON ─────────────────────────────────────────────────────────────────
    ("TRON Legacy digital frontier with cyan blue grid lines on matte black - geometric neon blue LED strips - identity disc desk lamp - digital world circuit board patterns",
     "Digital grid frontier with cyan blue neon lines on matte black - geometric neon blue LED strips - glowing disc desk lamp - digital circuit board patterns"),

    # ── THE MATRIX ───────────────────────────────────────────────────────────
    ("The Matrix digital rain coding station with terminal green falling code on black - green LED strips on ceiling - dystopian cyber aesthetic - red pill blue pill desk ornament",
     "Digital rain coding station with terminal green falling code on black - green LED strips on ceiling - dystopian cyber aesthetic - duality-choice desk ornament"),

    # ── TRANSFORMERS ─────────────────────────────────────────────────────────
    ("Transformers Bumblebee themed with bold yellow and black racing stripes - Autobot insignia LED wall art - mechanical joint styled cable routes - robot in disguise display",
     "Classic mech warrior themed with bold yellow and black racing stripes - faction emblem LED wall art - mechanical joint styled cable routes - machine in disguise display"),

    # ── BATMAN / DC GOTHAM ───────────────────────────────────────────────────
    ("Arkham Asylum madhouse with chaotic purple and toxic green - playing card LED displays - laughing gas fog machine - Joker smile neon wall sign - insanity-themed chaos aesthetic",
     "Dark madhouse with chaotic purple and toxic green - playing card LED displays - toxic gas fog machine - chaos grin neon wall sign - insanity-themed chaos aesthetic"),

    ("Gotham City underground vigilante headquarters with dark navy blue and black - city skyline LED silhouette - rain-on-window ambient effect - crime scene investigation board - noir",
     "Gothic dark city underground vigilante headquarters with navy blue and black - city skyline LED silhouette - rain-on-window ambient effect - crime scene investigation board - noir"),

    ("Gotham City Dark Knight themed batcave with all-black components and subtle yellow bat-signal accent LED - dark ambient only - crime-fighting command center aesthetic",
     "Dark gothic city vigilante cave with all-black components and subtle yellow search-signal accent LED - dark ambient only - crime-fighting command center aesthetic"),

    ("Gotham City cat burglar penthouse with sleek black leather and silver moonlight accents - diamond display case desk ornament - whip coiled cable management - stealthy luxury",
     "Gothic dark city cat burglar penthouse with sleek black leather and silver moonlight accents - diamond display case desk ornament - whip coiled cable management - stealthy luxury"),

    ("Robin's rooftop perch watchtower with traffic light red green gold on Gotham black night - bo staff display mount - acrobatic dynamic LED poses - holy gaming setup Batman",
     "Sidekick vigilante rooftop watchtower with traffic light red green gold on dark city night - bo staff display mount - acrobatic dynamic LED poses - dynamic duo gaming setup"),

    ("- Gotham-inspired stealth gaming setup with deep red ambient RGB",
     "- Gothic dark city-inspired stealth gaming setup with deep red ambient RGB"),

    ("- Dark multiverse-inspired battlestation with deep red RGB - Massive OLED ultrawide command center aesthetic - Matte black and carbon-fiber desk styling - Built for streaming, AAA gaming, and comic collector showcases",
     "- Dark dimension-inspired battlestation with deep red RGB - Massive OLED ultrawide command center aesthetic - Matte black and carbon-fiber desk styling - Built for streaming, AAA gaming, and comic collector showcases"),

    ("- Batcave-inspired battlestation with dark crimson ambient lighting",
     "- Vigilante cave-inspired battlestation with dark crimson ambient lighting"),

    ("- Gotham-inspired battlestation with dark crimson RGB",
     "- Gothic city-inspired battlestation with dark crimson RGB"),

    ("- Gotham-inspired command battlestation with stealth-red ambient lighting",
     "- Gothic city-inspired command battlestation with stealth-red ambient lighting"),

    ("- Gotham-inspired operations battlestation with stealth-red ambient lighting",
     "- Gothic city-inspired operations battlestation with stealth-red ambient lighting"),

    # ── IRON MAN ─────────────────────────────────────────────────────────────
    ("Tony Stark's lab vibes", "genius inventor's lab vibes"),

    # ── PERSONA 5 ────────────────────────────────────────────────────────────
    ("Persona 5 phantom thief inspired with bold red and black graphic design - calling card wall display - domino mask LED art - stylish rebellion aesthetic - never see it coming",
     "Phantom thief inspired with bold red and black graphic design - calling card wall display - domino mask LED art - stylish rebellion aesthetic - never see it coming"),

    # ── CYBERPUNK 2077 ───────────────────────────────────────────────────────
    ("Cyberpunk 2077 trauma team medic station with clinical teal and white accents on black - medical HUD display overlays - biometric monitoring aesthetic - night city emergency response",
     "Dystopian megacity trauma team medic station with clinical teal and white accents on black - medical HUD display overlays - biometric monitoring aesthetic - emergency response unit"),

    # ── SPIDER-MAN ───────────────────────────────────────────────────────────
    ("Spider-Man web-slinging station with red and blue web pattern RGB across black surfaces - web-styled cable management - Daily Bugle newspaper wall art - friendly neighborhood vibes",
     "Web-slinging hero station with red and blue web pattern RGB across black surfaces - web-styled cable management - city newspaper wall art - friendly neighborhood vibes"),

    # ── JURASSIC PARK ────────────────────────────────────────────────────────
    ("Jurassic Park genetics lab with amber fossilized mosquito display - DNA helix LED sculpture - jungle green and amber lighting - dinosaur skeleton model - life finds a way",
     "Prehistoric genetics lab with amber fossilized fossil display - DNA helix LED sculpture - jungle green and amber lighting - dinosaur skeleton model - nature always finds a way"),

    # ── DARK SOULS ───────────────────────────────────────────────────────────
    ("Dark Souls bonfire rest point with warm ember orange flickering on pitch black - coiled sword desk ornament - stone brick wall texture - foreboding yet comforting rest between battles",
     "Dark fantasy bonfire rest point with warm ember orange flickering on pitch black - coiled sword desk ornament - stone brick wall texture - foreboding yet comforting rest between battles"),

    # ── STAR TREK ────────────────────────────────────────────────────────────
    ("Star Trek starship bridge command center with LCARS blue and black interface panels - multi-display tactical array - flight control stick - warp speed starfield projector - engage",
     "Starship bridge command center with sci-fi blue and black interface panels - multi-display tactical array - flight control stick - warp speed starfield projector - full speed ahead"),

    # ── SUPERMAN / KRYPTON ───────────────────────────────────────────────────
    ("Kryptonian Phantom Zone prison with ethereal white flashes on void black - dimensional rift LED effects - crystal shard desk decorations - otherworldly prison dimension aesthetics",
     "Interdimensional void prison with ethereal white flashes on absolute black - dimensional rift LED effects - crystal shard desk decorations - otherworldly prison aesthetics"),

    # ── THOR / ASGARD ────────────────────────────────────────────────────────
    ("Norse Thunder God's throne with royal blue lightning and golden Asgardian accents - Mjolnir hammer desk ornament - rainbow bridge Bifrost LED strip - worthy of this setup",
     "Norse thunder deity throne with royal blue lightning and golden mythological accents - divine hammer desk ornament - rainbow bridge LED strip - worthy of this setup"),

    # ── SOLO LEVELING ────────────────────────────────────────────────────────
    ("Solo Leveling Shadow Monarch throne with dark purple shadow soldiers rising from black void - shadow tentacle LED effects - royal purple crown accent - absolute domination aesthetic",
     "Shadow warrior throne with dark purple shadow soldiers rising from black void - shadow tentacle LED effects - royal purple crown accent - absolute domination aesthetic"),

    # ── COBRA KAI ────────────────────────────────────────────────────────────
    ("Cobra Kai karate dojo with bold yellow and black snake emblem - martial arts training area aesthetic - nunchaku wall display - strike first strike hard no mercy LED sign",
     "Strike-first karate dojo with bold yellow and black snake emblem - martial arts training area aesthetic - nunchaku wall display - no mercy LED sign"),

    # ── TMNT ─────────────────────────────────────────────────────────────────
    ("Teenage Mutant Ninja Turtles underground sewer lair with green ooze glow and purple Foot Clan accents - pizza box desk organizer - ninjutsu dojo training area - cowabunga gaming den",
     "Underground mutant ninja sewer lair with green ooze glow and purple enemy clan accents - pizza box desk organizer - ninjutsu dojo training area - bodacious gaming den"),

    ("Radical turtle power party station with four-color turtle mask motif rotating LEDs - skateboarding halfpipe shelf design - bodacious neon arcade corner - heroes in a half shell",
     "Radical mutant ninja party station with four-color warrior mask motif rotating LEDs - skateboarding halfpipe shelf design - bodacious neon arcade corner - heroes in disguise"),

    ("Shredder's Technodrome command center with sharp blade silver chrome and dark purple - armored fortress aesthetic - Foot Clan insignia projectors - world domination plotting station",
     "Villain's armored fortress command center with sharp blade silver chrome and dark purple - armored fortress aesthetic - clan insignia projectors - world domination plotting station"),

    ("- TMNT arcade-inspired battlestation with sewer-green neon glow",
     "- Underground ninja arcade-inspired battlestation with sewer-green neon glow"),

    ("- TMNT sewer-hideout inspired setup with green arcade RGB",
     "- Underground sewer-hideout inspired setup with green arcade RGB"),

    ("- TMNT-inspired arcade battlestation with green retro RGB",
     "- Underground ninja arcade-inspired battlestation with green retro RGB"),

    ("- TMNT-inspired retro arcade battlestation with green neon RGB",
     "- Underground ninja retro arcade-inspired battlestation with green neon RGB"),

    ("- TMNT sewer-inspired", "- Underground sewer-inspired"),

    ("- TMNT-inspired arcade battlestation",
     "- Underground ninja arcade-inspired battlestation"),

    # ── MASTERS OF THE UNIVERSE ──────────────────────────────────────────────
    ("Masters of the Universe Castle Grayskull throne room with ancient stone and mystical gold power sword glow - by the power of Grayskull LED sign - barbarian king supreme gaming command",
     "Ancient power fortress throne room with stone and mystical gold power sword glow - ancient power LED sign - barbarian king supreme gaming command"),

    ("Snake Mountain dark villain fortress with skull face entrance glowing evil purple and bone white - Havoc Staff desk lamp - evil sorcerer laboratory aesthetic - NYAAA gaming lair",
     "Skull mountain dark villain fortress with skull face entrance glowing evil purple and bone white - evil staff desk lamp - sorcerer laboratory aesthetic - dark power gaming lair"),

    # ── WATCHMEN ─────────────────────────────────────────────────────────────
    ("Watchmen noir detective bunker with shifting inkblot black and white patterns - Doomsday Clock counting down - gritty vigilante aesthetic - never compromise LED sign",
     "Noir detective bunker with shifting inkblot black and white patterns - doomsday clock counting down - gritty vigilante aesthetic - never compromise LED sign"),

    # ── NIGHTMARE ON ELM STREET ──────────────────────────────────────────────
    ("Elm Street nightmare realm with blood red and sinister green stripe patterns on black void - dream catcher desk art - boiler room industrial pipes - one two Freddy's coming for your FPS",
     "Dream nightmare realm with blood red and sinister stripe patterns on black void - dream catcher desk art - boiler room industrial pipes - nightmare entity counting down gaming station"),

    # ── HALLOWEEN ────────────────────────────────────────────────────────────
    ("Haddonfield suburban horror with autumn orange pumpkin glow and pitch black shadows - October 31st desk calendar - kitchen knife letter opener - the shape is watching you game",
     "Suburban horror with autumn orange pumpkin glow and pitch black shadows - October 31st desk calendar - knife letter opener - the masked one is watching gaming station"),

    # ── IT (STEPHEN KING) ────────────────────────────────────────────────────
    ("Derry Maine sewer drain horror with single red balloon floating on absolute black - we all float down here neon sign - storm drain desk pen holder - fear feeding gaming station",
     "Small town sewer drain horror with single red balloon floating on absolute black - we all drift down here neon sign - storm drain desk pen holder - fear feeding gaming station"),

    # ── PREDATOR MOVIE ───────────────────────────────────────────────────────
    ("Arnold's commando jungle outpost with military OD green and mud brown on black - minigun desk replica - get to the chopper LED sign - guerrilla warfare gaming bunker",
     "Elite commando jungle outpost with military OD green and mud brown on black - minigun desk replica - mission evac LED sign - guerrilla warfare gaming bunker"),

    # ── RAMBO ────────────────────────────────────────────────────────────────
    ("Rambo First Blood survival camp with forest camo green and war-torn red bandana accent - survival knife display stand - POW rescue mission map wall - they drew first blood",
     "Survivalist's wilderness camp with forest camo green and war-torn red bandana accent - survival knife display stand - rescue mission map wall - they drew first blood survival gaming"),

    # ── SHAZAM ───────────────────────────────────────────────────────────────
    ("SHAZAM lightning bolt strike with electric gold bolt on thunderstorm black - thunder crack LED ceiling strip - wisdom of Solomon study corner - say my name gaming power",
     "Lightning hero strike with electric gold bolt on thunderstorm black - thunder crack LED ceiling strip - ancient wisdom study corner - say the word gaming power"),

    # ── PEACEMAKER (DC) ──────────────────────────────────────────────────────
    ("Peacemaker patriotic peace mission HQ with clean white and chrome red-blue accents - bald eagle desk statue - peace through overwhelming firepower sign - do you really wanna taste it",
     "Patriotic peace mission HQ with clean white and chrome red-blue accents - bald eagle desk statue - peace through strength sign - warrior's creed gaming station"),

    # ── STATIC SHOCK (DC) ────────────────────────────────────────────────────
    ("Dakota City Static Shock electricity lab with crackling blue lightning bolts and gold static charge on black - Tesla coil desk ornament - electromagnetic field LED strips - I put a shock to your system",
     "Urban electric hero's electricity lab with crackling blue lightning bolts and gold static charge on black - Tesla coil desk ornament - electromagnetic field LED strips - electric charge to your system"),

    # ── NEON GENESIS EVANGELION ──────────────────────────────────────────────
    ("Neon Genesis Evangelion Unit-01 inspired with signature purple and green on black - NERV logo LED art - entry plug ambient lighting - cruel angel's thesis BGM",
     "Giant mech unit inspired with signature purple and green on black - organization emblem LED art - cockpit ambient lighting - iconic mech theme BGM"),

    # ── ATTACK ON TITAN ──────────────────────────────────────────────────────
    ("Attack on Titan inspired setup with warm orange lighting - White gaming station contrasted with dramatic anime décor - Ultrawide OLED for immersive story-driven gameplay - Collector-focused desk with manga-inspired accents",
     "Titan slayer inspired setup with warm orange lighting - White gaming station contrasted with dramatic anime décor - Ultrawide OLED for immersive story-driven gameplay - Collector-focused desk with manga-inspired accents"),

    ("- Attack on Titan inspired setup with warm orange lighting",
     "- Titan slayer inspired setup with warm orange lighting"),

    ("- Attack on Titan-inspired battlestation with blue aura RGB",
     "- Titan slayer-inspired battlestation with blue aura RGB"),

    ("- Attack on Titan-inspired battlestation with warm orange lighting",
     "- Titan slayer-inspired battlestation with warm orange lighting"),

    # ── DRAGON BALL ──────────────────────────────────────────────────────────
    ("Dragon Ball-inspired battlestation with gold and blue aura RGB - White OLED gaming station with glowing anime shelves - Elegant collector-focused setup with premium airflow design - Competitive gaming performance blended with anime luxury",
     "Legendary power warrior battlestation with gold and blue aura RGB - White OLED gaming station with glowing anime shelves - Elegant collector-focused setup with premium airflow design - Competitive gaming performance blended with anime luxury"),

    ("- Dragon Ball-inspired battlestation with gold and blue aura RGB",
     "- Legendary power warrior battlestation with gold and blue aura RGB"),

    ("- Dragon Ball-inspired battlestation with gold-blue aura RGB",
     "- Legendary power warrior battlestation with gold-blue aura RGB"),

    ("- Dragon Ball-inspired battlestation with gold aura RGB",
     "- Legendary power warrior battlestation with gold aura RGB"),

    ("- Shenron-inspired", "- Legendary dragon-inspired"),

    # ── MARVEL (GENERAL) ─────────────────────────────────────────────────────
    ("Avengers-inspired RGB command station with blue and gold lighting - OLED ultrawide centerpiece for immersive AAA gaming - Figure display integrated into shelving around monitors - Premium white-and-silver luxury aesthetic",
     "Superhero team-inspired RGB command station with blue and gold lighting - OLED ultrawide centerpiece for immersive AAA gaming - Figure display integrated into shelving around monitors - Premium white-and-silver luxury aesthetic"),

    ("- Cosmic Marvel-inspired battlestation with blue and gold RGB",
     "- Cosmic superhero-inspired battlestation with blue and gold RGB"),

    ("- Cosmic Marvel-inspired battlestation with blue-white ambient lighting",
     "- Cosmic superhero-inspired battlestation with blue-white ambient lighting"),

    ("- Marvel-inspired luxury battlestation with blue and gold ambient lighting",
     "- Superhero-inspired luxury battlestation with blue and gold ambient lighting"),

    ("Mystical Marvel décor integrated into shelving and lighting",
     "Mystical superhero décor integrated into shelving and lighting"),

    ("Marvel collector", "superhero collector"),
    ("Marvel décor", "superhero décor"),
    ("Marvel shelves", "superhero shelves"),
    ("Marvel Cosmic", "cosmic superhero"),

    # ── JUSTICE LEAGUE ───────────────────────────────────────────────────────
    ("- Justice League-inspired luxury battlestation with blue ambient RGB",
     "- Superhero alliance-inspired luxury battlestation with blue ambient RGB"),

    ("- Justice League-inspired battlestation with blue-white ambient lighting",
     "- Superhero alliance-inspired battlestation with blue-white ambient lighting"),

    ("- Justice League-inspired luxury battlestation with blue-white ambient lighting",
     "- Superhero alliance-inspired luxury battlestation with blue-white ambient lighting"),

    ("- Justice League-inspired battlestation with blue-white cinematic RGB",
     "- Superhero alliance-inspired battlestation with blue-white cinematic RGB"),

    ("- Justice League-inspired battlestation with blue-white cinematic lighting",
     "- Superhero alliance-inspired battlestation with blue-white cinematic lighting"),

    # ── WAKANDA / VIBRANIUM ──────────────────────────────────────────────────
    ("Wakandan vibranium tech throne with deep purple and black vibranium-weave patterns - holographic tech displays - panther mask LED wall art - advanced African futurism aesthetic",
     "Advanced Afrofuturist tech throne with deep purple and black metallic-weave patterns - holographic tech displays - panther mask LED wall art - advanced African futurism aesthetic"),

    # ── WINTER SOLDIER ───────────────────────────────────────────────────────
    ("Winter Soldier cold war bunker with silver mechanical arm chrome and tactical black - cryo chamber LED blue accent - Soviet red star detail - programmed assassin aesthetic",
     "Cold war bunker with silver mechanical arm chrome and tactical black - cryo chamber LED blue accent - red star detail - programmed assassin aesthetic"),

    # ── MECHAGODZILLA (theme descriptions) ──────────────────────────────────
    ("Secret Mechagodzilla construction lab with blueprint wireframe LED displays - mechanical schematic wallpapers - robot joint desk lamp - titanium alloy aesthetic - monster machine",
     "Secret titan machine construction lab with blueprint wireframe LED displays - mechanical schematic wallpapers - robot joint desk lamp - titanium alloy aesthetic - colossal machine"),

    # ── THUNDERCATS ──────────────────────────────────────────────────────────
    ("ThunderCats Third Earth lair with Sword of Omens eye emblem LED - blue and red thunder accents - cat's lair styled desk - thunder thunder ThunderCats HOOO",
     "Legendary cat warrior lair with eye-of-power emblem LED - blue and red thunder accents - mountain fortress styled desk - thunder warrior battle cry"),

    # ── INITIAL D ────────────────────────────────────────────────────────────
    ("Initial D mountain pass wallpaper - touge king", "mountain pass wallpaper - drift king"),

    # ── FALLOUT / PIP-BOY ────────────────────────────────────────────────────
    ("Pip-Boy styled interface overlays", "retro terminal styled interface overlays"),
    ("Pip-Boy Styled Clock", "Retro Terminal Clock"),

    # ── GREEN LANTERN ────────────────────────────────────────────────────────
    ("Green Lantern Corps emerald knight with willpower green constructs on black void - power ring desk lamp - emerald crystal formations - in brightest day gaming station",
     "Emerald warrior corps with willpower green energy constructs on black void - energy ring desk lamp - emerald crystal formations - in brightest day gaming station"),

    ("- Emerald-powered superhero battlestation with reactive green RGB",
     "- Emerald warrior-powered battlestation with reactive green RGB"),

    # ── REMAINING SPECIFIC PHRASES ───────────────────────────────────────────
    ("Star Wars collector", "sci-fi space collector"),
    ("Galactic Empire", "space empire"),
    ("Sith Empire", "dark space empire"),
    ("Sith throne", "dark emperor throne"),
    ("Sith-inspired", "dark warrior-inspired"),
    ("Jedi Temple", "ancient temple"),
    ("Jedi Order", "space guardian order"),
    ("Clone Wars", "space military war"),
    ("Rebel Alliance", "space rebel alliance"),
    ("Imperial white-themed", "pristine white-themed"),
    ("Star Wars", "sci-fi space"),
    ("TRON", "digital grid"),
    ("The Matrix", "digital simulation"),
    ("Transformers", "shape-shifting mech"),
    ("Autobot", "faction"),
    ("Gotham City", "gothic dark city"),
    ("Gotham-inspired", "gothic city-inspired"),
    ("Arkham Asylum", "dark madhouse"),
    ("batcave", "vigilante cave"),
    ("bat-signal", "hero signal"),
    ("Demon Slayer", "spirit blade warrior"),
    ("Solo Leveling", "shadow warrior manhwa"),
    ("Cobra Kai", "strike-first dojo"),
    ("Persona 5", "phantom thief"),
    ("Cyberpunk 2077", "dystopian megacity"),
    ("Neon Genesis Evangelion", "giant mech anime"),
    ("NERV", "mech organization"),
    ("Spider-Man", "web-slinging hero"),
    ("Daily Bugle", "city newspaper"),
    ("Jurassic Park", "prehistoric genetics"),
    ("Dark Souls", "dark fantasy"),
    ("LCARS", "sci-fi interface"),
    ("Kryptonian", "alien superhero"),
    ("Phantom Zone", "interdimensional void prison"),
    ("Mandalorian", "bounty hunter warrior"),
    ("beskar", "battle-forged steel"),
    ("vibranium", "advanced fictional metal"),
    ("Wakandan", "Afrofuturist"),
    ("Wakanda", "Afrofuturist nation"),
    ("Asgardian", "Norse mythological"),
    ("Mjolnir", "divine thunder hammer"),
    ("Bifrost", "rainbow bridge"),
    ("Justice League", "superhero alliance"),
    ("Avengers", "superhero team"),
    ("Marvel", "superhero"),
    ("Attack on Titan", "titan slayer"),
    ("Dragon Ball", "legendary power warrior"),
    ("ThunderCats", "thunder warrior cats"),
    ("Watchmen", "graphic novel vigilante"),
    ("Rorschach", "inkblot vigilante"),
    ("TMNT", "underground ninja turtles"),
    ("Foot Clan", "enemy ninja clan"),
    ("Technodrome", "villain fortress"),
    ("Masters of the Universe", "sword-and-sorcery"),
    ("Castle Grayskull", "ancient power fortress"),
    ("Havoc Staff", "evil sorcerer staff"),
    ("Elm Street", "nightmare street"),
    ("Haddonfield", "suburban horror town"),
    ("the shape is", "the masked one is"),
    ("Derry Maine", "small town horror"),
    ("we all float", "we all drift"),
    ("Arnold's commando", "elite commando"),
    ("get to the chopper", "mission evacuation"),
    ("Rambo First Blood", "survivalist's blood trail"),
    ("SHAZAM", "lightning hero"),
    ("Peacemaker", "peace enforcer"),
    ("Static Shock", "electric hero"),
    ("Dakota City", "urban city"),
    ("Kylo Ren", "dark heir warrior"),
    ("First Order", "dark faction"),
    ("Conan", "ancient barbarian"),
    ("Atlantean sword", "legendary ancient sword"),
    ("Initial D", "touge racing"),
    ("Pip-Boy", "retro terminal"),
    ("Green Lantern", "emerald warrior"),
    ("by the power of Grayskull", "by the ancient power"),
]


def apply_replacements(text):
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def main():
    # Read the CSV preserving original structure
    with open(INPUT_FILE, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames
    rows = list(reader)

    theme_col = "Theme"
    changed = 0

    for row in rows:
        original = row[theme_col]
        cleaned = apply_replacements(original)
        if cleaned != original:
            row[theme_col] = cleaned
            changed += 1

    # Write back
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {changed}/{len(rows)} theme descriptions updated.")


if __name__ == "__main__":
    main()
