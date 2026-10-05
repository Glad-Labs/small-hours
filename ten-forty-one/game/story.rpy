## Ten Forty-One: the written scenes of the slice. The prologue, the discovery, every clue, every belief
## overturned, every clock event. The loop that runs between them is in script.rpy; the case is in case.py.
##
## House style: the detective's own thoughts are `think` (italics). Narration notices things; it does not
## explain them. Nobody spells out a deduction the player can make, but every plant is on screen at least once.

default talked = []         # prologue: who the detective spoke to before the sale
default met = []            # chapter 1: who has had their first-meeting lines
default others_count = 0    # which of the rotating Dom/Ibarra lines comes next


## ---------------------------------------------------------------------------------------------
## Prologue
label prologue:
    scene bg letter with fade
    "Three days ago a letter reached you on heavy cream paper, the gallery's crest pressed into one corner."
    "{i}Detective. There are irregularities in the Calder provenance that I cannot raise with anyone in my own house. Discretion is essential. Come to Thursday's sale as my guest.{/i}"
    "{i}Edmund Harrow.{/i}"
    think "The sale was advertised for Saturday. Somebody moved it to Thursday."
    think "Thursday's forecast was the worst of the year. People who want discretion don't usually pick the night the whole coast is watching the weather."
    think "Still. A man asks for help, you go."

    scene bg bridge with dissolve
    "6:00 pm. The lift bridge to the headland is a single lane of iron, and it shudders under your tyres like something alive."
    "Behind you the channel is already white. Ahead, the old customs house sits on its rock with every window lit, like a ship that has decided not to sink."
    think "One road in. One road out. I've worked in worse places. Not many."

    scene bg hall with dissolve
    "The Harrow Gallery was a customs house once. It still looks as if it expects to tax you."
    "Green walls, gilt frames, chandeliers like frozen fireworks. Rows of chairs facing a rostrum, and a dozen people pretending they haven't all come for the same painting."

    show nell warm at right_spot with dissolve
    nell_c "You must be the detective. Nell Ashby, registrar. Programme."
    "She hands it over with her left hand. There's ink on her fingers, blue to the second knuckle, and she doesn't seem to have noticed."
    nell_c "Lot nine is the one everyone's pretending not to want. The bar's on the left. Please don't touch Untitled (Chair)."
    det "What happens if I touch the chair?"
    nell_c "Nothing. It's a chair. But Edmund paid forty thousand for it, so we all have to act as if it's holy."
    nell_c "If you need anything, I'm the one who knows where everything is. Including the exits. Especially the exits."
    think "The first person tonight who's looked at me like a person and not a rumour."
    hide nell with dissolve

    show webb calm at left_spot with dissolve
    "At the rostrum, a lean man in a silver-grey waistcoat is polishing a gavel with an ivory handle, slowly, the way some men clean a gun."
    webb_c "You're the detective. Marcus Webb, Aldous & Pryce. I've read about you, my dear. The Marlowe business. Closed in a single night."
    webb_c "And this is my grandfather's gavel. It has sold three Constables, a Turner that turned out not to be, and a ghost."
    det "A ghost."
    webb_c "A haunted wardrobe, Hampshire, 1974. The ghost was not included in the reserve."
    webb_c "I like things exact. The hammer falls at a time, not around one. You'll see."
    hide webb with dissolve

    "Across the room a stout man in a velvet jacket is holding court, laughing a beat too loud. Edmund Harrow, judging by the space the others give him."
    "Beside him a thin man in a cardigan rubs his hands together. Julian Crane, says your programme: the authenticator, hired to put his name to the Calder lots."
    crane "It's the vault. They keep it at twelve degrees for the canvases. I've been down there all afternoon."
    harrow "Julian, you're blue. Take my coat. No, I insist. I've a jacket and an excellent cellar."
    "Harrow drapes a camel overcoat over Crane's shoulders. It swamps him. He looks like a boy wearing his father's coat to a funeral."
    crane "Thank you, Edmund. I'll go down for one more look at the interval. Late works are like witnesses. They tell you the truth at the end, if you let them."
    "Harrow's smile doesn't move at all."

    "A grey-haired caretaker shoulders past with a crate of wine, talking to nobody in particular."
    pike "Thirty years I've kept that cellar locked. Tonight it's propped open for the wine. Whoever's idea that was."
    think "Not his, clearly."

    "The sale starts at half past eight. There's time for a word with two people before then."
    $ talked = []
label prologue_mingle:
    menu:
        "Edmund Harrow, your host" if "harrow" not in talked:
            $ talked.append("harrow")
            harrow "Detective! Delighted, delighted. You have a drink? You must have a drink. Nell will..."
            harrow "Is something the matter?"
            menu:
                "Thank him for the invitation":
                    det "Just your letter, Mr Harrow. I came as soon as I could."
                    harrow "Letter?"
                    "His smile stays where it is. His eyes don't."
                    harrow "I wrote you no letter. I don't... Who told you to come here?"
                    det "You did. On your own paper."
                    harrow "Then somebody has my paper."
                    $ harrow_denied = True
                    "Before you can answer, Webb calls his name from the rostrum, bright as a bell, and Harrow goes like a man glad of the excuse."
                    think "Either Edmund Harrow is a very good liar, or someone else wanted me here tonight. I'm not sure which I like less."
                "Ask about the Calder works":
                    det "Tell me about the Calder works."
                    harrow "Magnificent. Late, unfinished, raw. Calder at the end, painting like a man running out of time."
                    harrow "Found in his studio after he died. Nine canvases nobody knew existed. They will make history tonight."
                    "He says it to a point somewhere over your left shoulder, and he doesn't meet your eyes once."

        "The young man at the bar" if "dom" not in talked:
            $ talked.append("dom")
            dom "Dom Harrow-Bell. Nephew, heir, family embarrassment. Don't get up."
            det "I'm standing."
            dom "Then don't sit down. The chairs are for sale."
            dom "Funny, isn't it, holding it tonight. It was meant to be Saturday. Then on Monday, suddenly, Thursday."
            det "Why the change?"
            dom "Uncle Eddie says the buyers fly out on Friday. Uncle Eddie says a lot of things. Mostly to the bank."

        "The man by the terrace doors" if "ibarra" not in talked:
            $ talked.append("ibarra")
            ibarra "Tomás Ibarra. Physician, collector, insomniac. In roughly that order of success."
            ibarra "You're the detective. Don't look surprised. There are a dozen guests, and only one of them keeps checking the exits."
            "His phone buzzes. He glances at the screen, and something goes out of his face."
            ibarra "Forgive me. I have to take this."
            "He steps out onto the terrace into the rain with the phone already at his ear, and the door swings shut behind him."

    if len(talked) < 2:
        jump prologue_mingle

    scene bg hall with dissolve
    "8:30 pm. The sale begins."
    show webb calm at left_spot with dissolve
    webb_c "Lot one. A study in charcoal, and a very fine one. Do I hear eight? Eight, thank you, sir. Nine on the telephone. Ten in the room..."
    "Webb is very good. Inside ten minutes he has a room full of rich people feeling poor."
    webb_c "Going once. Going twice. Sold, to the gentleman who will be explaining this to his wife on the drive home."
    hide webb with dissolve
    "9:00 pm. The interval. The room breaks up toward the bar, the terrace and the corridors, and you lose sight of half of them inside a minute."
    "Crane, in Harrow's coat, heads down the corridor toward the vault for his last look."
    "9:40 pm. The sale resumes."
    "Webb raps the block for silence, and it isn't the ivory gavel any more. It's a plain boxwood one, the kind a house keeps in a drawer."
    think "Strange time to change a lucky hammer."
    "10:35 pm. Lot nine at last. Harrow slips out of the hall. Pike goes for the vault keys to bring the painting up."
    "Out of habit, you count the room."
    "Webb at the rostrum. Nell at the catalogue desk. Dom at the bar. Ibarra by the window. Everyone but Harrow and Pike."
    show webb calm at left_spot with dissolve
    webb_c "While we wait for lot nine, ladies and gentlemen... ten forty-one, and the storm is putting on quite a show for us."
    scene bg black
    "10:41 pm. The lights die."
    "One second. Two. Somebody laughs, too high. A glass breaks."
    "The lights stutter back on. Every clock in the hall has stopped."
    "Three minutes later, a shout from the vault corridor."
    pike "Mr Harrow! Somebody! Mr Harrow's dead!"
    jump chapter_one


## ---------------------------------------------------------------------------------------------
## Chapter 1: The Wrong Body.
label chapter_one:
    $ place = "vault"
    scene bg vault with fade
    "10:48 pm. You get there first, because you're the only one who ran toward the shout."
    "The vault door hangs open on its emergency override. Pike stands in the doorway with the key still in his fist and the colour gone out of him."
    pike "I couldn't open it. Bolted from inside. Had to use the override. Thirty years, I've never once had to use the override."
    "A man lies face down on the concrete in a camel coat, one arm folded under him."
    think "Harrow's coat. Everyone in the hall watched him give it away."
    "You kneel and turn him over."
    $ found.append("body")
    "It isn't Harrow. It's Julian Crane, swamped in Harrow's coat, a flat, round dent in the back of his skull."
    "Three hours ago he was telling you that paintings are honest at the end."
    "In the coat's inside pocket, a notebook. The last page, in a small, tidy hand: {i}strokes left-handed. Do not certify.{/i}"
    "His watch is smashed. It reads 10:41."
    show webb calm at left_spot
    show nell calm at right_spot
    with dissolve
    nell_c "Oh, God. Julian."
    webb_c "Ten forty-one. Every clock in the house says it, and so does his watch. The moment the lights went."
    webb_c "Write that down, my dear. It will matter later, and people forget."
    nell_c "The door was bolted from the inside. Pike had to use the override. There's no other way in."
    pike "And Mr Harrow's not in his study. I looked. He's not anywhere."
    webb_c "His coat. His vault. And now he's gone. I hate to say it. I truly do."
    "Ibarra pushes in behind them, kneels, and touches two fingers to Crane's neck, out of habit more than hope."
    ibarra "He's dead. I'm a physician, not a coroner, so don't ask me for the hour. It's twelve degrees in here. Cold rooms make liars of bodies."
    "Dom appears in the doorway with his glass still in his hand, and looks at the body for a long second."
    dom "Well. That's the sale ruined."
    nell_c "Dom."
    dom "Sorry. I say stupid things when I'm frightened. It runs in the family."
    det "Nobody touches anything. And nobody leaves the house."
    webb_c "Nobody's going anywhere in this weather, my dear. You have until dawn. Use it well."
    hide webb
    hide nell
    with dissolve
    $ assumptions[:] = list(case.ASSUMPTION_ORDER)
    "You open your notebook. Before you've written a word of your own, the room has already written three for you."
    "{b}Crane died at 10:41.{/b}   {b}The vault was sealed.{/b}   {b}Harrow killed him and ran.{/b}"
    think "Everybody agreed in under a minute. That's usually when I start to worry."
    think "Nobody can cross the bridge before the sheriff comes at dawn, and I don't trust the lights in this place."
    "Every search, walk and question moves the clock. Open your notebook to challenge what everyone believes."
    $ minute = case.START
    jump investigate


## ---------------------------------------------------------------------------------------------
## First meetings, before the free-text questions.
label meet_webb:
    webb_c "Detective. Sit, if you like. There are forty chairs and I've sold none of them tonight."
    webb_c "Ask me anything you like. I've nothing to hide but my commission."
    return

label meet_nell:
    nell_c "If you're going to interrogate me, let me sit down first. My knees have opinions."
    nell_c "Go on, then. I'll tell you anything that isn't about Edmund's accounts. Those frighten even me."
    return


## Dom and Ibarra are not voiced in this chapter; they say one of these each time, in turn, and some of them
## point somewhere the player may not have looked yet.
init python:
    OTHERS = [
        ("dom", "Uncle Eddie used to hide in the boathouse when Aunt Celia was cross with him. I'm just saying. If I were Uncle Eddie."),
        ("ibarra", "I've told the caretaker everything I know, which is nothing. I'd like to keep it that way."),
        ("dom", "Have you seen Webb's gavel? Not the house one. The good one, the ivory one. He was waving it about all evening, and then poof. Who steals a gavel?"),
        ("ibarra", "That registrar keeps looking over at you. Either she likes you or she's afraid. In my experience those look identical."),
        ("dom", "Nell knows every inch of this place. When I was nine she found me in a cupboard I didn't know existed. I still don't know where it was."),
        ("ibarra", "Every clock in the house, the very same minute. I've been at a great many deaths, Detective. Time is never that tidy."),
        ("dom", "The fuses in this building are older than I am. Pike won't let anybody near the cupboard. Well. He didn't."),
        ("ibarra", "I was on the terrace for most of the interval, if you're keeping a list. On the telephone. Please don't ask with whom."),
    ]

label others:
    python:
        who, line = OTHERS[others_count % len(OTHERS)]
        others_count += 1
    if who == "dom":
        dom "[line!q]"
    else:
        ibarra "[line!q]"
    return


## ---------------------------------------------------------------------------------------------
## Beliefs overturned in the notebook, and the steps toward them.
label broke_a_time(clue):
    if clue == "chart":
        think "The chart doesn't care what the clocks say. At 9:31 the warmth of a living man went out of that room."
    else:
        think "9:26, read. 9:45, never opened. Julian Crane was dead before ten."
    think "So 10:41 is a lie. And somebody went to a great deal of trouble to tell it: the clocks, the watch, the lights."
    think "Every alibi for 10:41 is worthless now. Including the one I watched with my own eyes: Webb, on the rostrum, saying the time out loud."
    "{b}Struck out:{/b} Crane died at 10:41."
    return

label broke_a_sealed(clue):
    think "Bolted from the inside, with a way out the size of a grille hidden behind the frames. The vault was never sealed."
    think "It was only sealed for anyone who didn't know about the duct."
    think "And Nell, who knows where everything in this building is, told me there was no other way in."
    "{b}Struck out:{/b} The vault was sealed."
    return

label broke_a_harrow(clue):
    think "Whoever killed Crane left through that duct, and in a hurry."
    think "Harrow is built like a wardrobe. He'd stick at the shoulders before he got his elbows in."
    think "Whoever crawled out of that vault was slim. Edmund Harrow is nobody's idea of slim."
    "{b}Struck out:{/b} Harrow killed him and ran."
    return

label hint_a_time_watch:
    think "The crown is pulled out. Somebody set this watch to 10:41 with their own fingers."
    think "That proves the time was faked. It doesn't tell me when he really died. Something in this house must have kept honest time."
    return

label hint_a_time_timer:
    think "The clocks stopped because a timer told them to, at a minute somebody chose."
    think "So the time was staged. Then when did he really die? Something down here wasn't on the mains."
    return

label hint_a_harrow_letter:
    think "Harrow was frightened of something, enough to burn a confession. Frightened men run."
    think "They don't always kill. Sometimes they're the next one."
    return

label impossible_crime:
    think "Wait."
    think "If Crane died at 10:41, then nobody could have killed him."
    think "At 10:41 every slim person in this house was standing in front of me in the hall. I counted them."
    think "The only two who weren't, Harrow and Pike, could never get through that duct."
    think "So he didn't die at 10:41. Somebody wanted me to believe he did. Prove it."
    return


## ---------------------------------------------------------------------------------------------
## Finding things. Each label narrates one clue from case.py.
label clue_watch:
    "Crane's watch is a plain steel thing, the kind a careful man buys once and wears for thirty years."
    "The crystal is smashed. The hands stand at 10:41."
    "But the crown, the little winding knob on the side, is pulled all the way out."
    think "A watch doesn't stop like that when you fall on it. It stops like that when somebody is setting it."
    return

label clue_duct:
    "You go round the walls slowly, the way you'd go round a stranger's flat."
    "The bolt on the door is thrown from the inside. Pike's override sheared the keeper clean off the frame."
    "Low on the back wall, behind a rack of wrapped frames, an old iron grille sits off its screws, leaning against the concrete."
    "Behind it, a square of darkness, and a cold draught that smells of wine and wet stone."
    think "An air duct. The customs men must have vented the bonded store through it. Big enough for someone slim to crawl along. Someone big would stick at the shoulders."
    think "\"There's no other way in,\" Nell said."
    return

label clue_chart:
    "On a shelf by the door sits a climate recorder: a brass drum wrapped in graph paper, turned by a clockwork spring, a pen nib tracing the vault's warmth and damp."
    "It doesn't run off the mains. The lights going out wouldn't have stopped it."
    "You follow the line with a fingertip. Flat all afternoon. At 9:14 it starts to climb, the way it would with somebody shut in a small room, breathing."
    "At 9:31 it turns, and falls away, slowly, all the way down."
    think "That isn't a machine. That's a man getting cold."
    return

label clue_phone:
    "Crane's phone is in his trouser pocket. No lock screen. He trusted people."
    "A text from his wife at 9:26: {i}don't let them bully you x{/i}. Read."
    "Another at 9:45: {i}ring me when you're done? love you{/i}. Never opened."
    think "Nineteen minutes between a man who reads his messages and a man who can't."
    return

label clue_thread:
    "The duct comes out low in the cellar wall, behind the wine racks, where nobody would look unless they were crawling."
    "The grille here is back on its screws, but only finger-tight. The dust in front of it has been swept flat by something the size of a person."
    "Caught on the grille's sharp edge: a single thread of wool. Silver-grey. Fine. Expensive."
    think "Whoever came through here was in a hurry, and dressed for an evening out."
    return

label clue_timer:
    "The fuse cupboard is a grey steel box whose door won't quite shut. Inside, rows of old ceramic fuses, cobwebbed and labelled in faded pencil."
    "And one thing that isn't old: a white plug-in timer, the kind you buy for a lamp, fitted to the circuit marked {i}CLOCKS{/i}."
    "Its little dial is set to cut the power at 10:41 and restore it at 10:42."
    think "Every clock in the house stopped because somebody told it to. Somebody wanted the whole room to remember that minute."
    return

label clue_gavel:
    "Behind the racks stands a bin of packing straw and broken bottles that smells of sour wine."
    "You go through it with a handkerchief over your hand. Near the bottom, wrapped in a bar rag, something heavy."
    "An ivory-handled gavel. The head is cracked right across, and the crack is stained dark brown."
    think "I've seen this before tonight. It sold three Constables and a ghost."
    return

label clue_letter:
    "Harrow's study smells of cigar and old leather and, faintly, of smoke. The grate behind the desk is still warm."
    "In the ashes, one page hasn't burned all the way. His handwriting, big and looping, the hand of a man used to signing things."
    "{i}...I can no longer pretend. Every Calder sold since 2019 through Aldous & Pryce is...{/i}"
    "The rest is black."
    think "Is what? Wonderful? Overpriced? Fake? People don't burn letters that say wonderful."
    return

label clue_shelf:
    "Nell's office is the tidiest room in the building. Labelled boxes, labelled drawers, a pot of pens sorted by colour."
    "On the shelf behind her desk every binder sits under a neat typed label. One label sits over nothing at all."
    "{i}CALDER: SALES LEDGER.{/i}"
    think "A woman this tidy doesn't lose a ledger. She moves one."
    return


## ---------------------------------------------------------------------------------------------
## Clock events.
label event_phones:
    scene bg hall
    "10:58 pm. The terrace door bangs open and Pike comes in out of the storm, soaked to the waist, a torch in one hand."
    pike "Phones are dead. Landline too. I went out to the box on the garden wall."
    pike "Line's cut. Clean, like with snips. That's not the wind."
    dom "So we can't call the police. Marvellous. Can we call a priest?"
    nell_c "Pike, what about the mobiles?"
    pike "Not a bar on this headland in weather like this. Never has been."
    think "Somebody knew that, too."
    return

label event_bridge:
    scene bg hall
    "11:05 pm. Pike again, out of breath, rain running off him onto the parquet."
    pike "Went down to lower the bridge. Just in case. It won't come down."
    pike "Pump's dead. The fuse is gone from the box. Not blown. Gone. Somebody took it out and took it away."
    nell_c "Then we're stuck here. All of us. With..."
    "She doesn't finish. She doesn't need to."
    webb_c "Then we wait for dawn like civilised people. There's a great deal of very good wine, and I'm told the sheriff is an early riser."
    think "The storm didn't trap us here. Somebody did. And whoever it was planned this night right down to the fuse."
    return

label event_lights_out:
    scene bg black with Dissolve(1.0)
    "11:30 pm. Somewhere below you the generator coughs twice, like a man trying not to wake anyone. Then it stops."
    "Every light in the Harrow Gallery goes out at once."
    "In the dark the storm sounds closer: rain hammering the tall windows, and somebody near you breathing quick and shallow."
    nell_c "Detective? Are you still there?"
    det "I'm here."
    nell_c "Good. Stay there. I mean... stay where I can hear you."
    dom "Brilliant. Locked in a haunted customs house with a murderer and no lights. I'd like to speak to the manager."
    pike "I'll fetch candles. Nobody wanders off."
    webb_c "Nobody move. My dear, nobody move at all."
    think "He sounds calm. He's the only one who does."
    "Somewhere in the house, very softly, a door closes."
    $ renpy.call_screen("slice_end")
    $ end_game()
    return
