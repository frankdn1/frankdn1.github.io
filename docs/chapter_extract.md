# Prompt for Coding Agent: Split `book.txt` into Chapter Files

## Task Summary

You are given a text file named `book.txt` that contains the full contents of a book. Your job is to:

1. Parse the table of contents (TOC) from the top of the file.
2. Extract each chapter based on the TOC.
3. Save each chapter as an individual `.txt` file in a folder called `chapters/`.

## File Naming

Each file should follow this naming format:

NN_Chapter_Title.txt

Where:
- `NN` is the chapter number with leading zeros (e.g., 01, 02).
- `Chapter_Title` is the sanitized version of the chapter title, using underscores `_` for spaces and removing special characters.

**Example:**
If a chapter is titled *"My Earlier Years that I Can Remember"*, and it's the first chapter, the filename should be:

01_My_Earlier_Years_that_I_Can_Remember.txt

## Parsing Instructions

- The TOC appears before the first actual chapter and includes lines in this format:
Chapter Title <tab> Page Number

Example:
My Earlier Years that I Can Remember 1 

Hunting and Fishing in The Yukon 37

- Use the chapter titles from the TOC to split the full text into sections. Each chapter begins with its title as a heading.

- Save each chapter's content from its title to just before the next chapter's title.

- Some chapters contain special character which you must deal with such as "Learning the area around St. John’s, Newfoundland	67"  The period, quote and comma should be removed from the file name so as to not cause issues. 

## Edge Cases

- Ignore page numbers in the TOC; they're just hints.
- Some chapter titles may include punctuation like periods or dashes—sanitize these when naming files.
- Ensure all content from each chapter is fully captured, including multiline paragraphs.

## Output

All resulting `.txt` chapter files must be placed in a folder named `chapters` in the same directory as the script.

## Chapters

You will know you have this task compete when you have a text file for each of the chapters listed below.

My Earlier Years that I Can Remember	1

Hunting and Fishing in The Yukon	37

The Story Of The .219 Zipper Improved Rifle	57

Brief Info On Some Events In Newfoundland	61

Learning the area around St. John’s, Newfoundland	67

Royal Newfoundland Yacht Club	76

Yukon Flotilla 1967	82

Dealing with The Cold Weather	94

Choosing the Right Police Firearm	113

Refurbishing the RCMP Graveyard at Dawson City, Y.T.	126

Digging Graves In The RCMP Cemetery	138

Dangerous Grizzly Bear Encounter	141

Attempted bank robbery at Dawson City	147

Dawson City flood in 1964	151

Wolf Troubles	158

Trip up the Sixty Mile River	169

Stewart River’s trip from Dawson City	177

Time at Dawson City Postings	181

Seizure of Illegal Two-Way Radios	193

Checking on the Prisoner Work Gang	198

Looking after the Aboriginal Affairs and Northern Development file	199

Hard lesson on learning the social structure of local natives	214

Major accident south of Watson Lake	217

Murder near Watson Lake, Yukon Territory 1967	220

Pipeline Break - Up The Canol Road	230

Search For The Swiss Mountain Climbers On The Nahanni River	248

Fort McPherson Grave Site Maintenance	259

Making a difficult arrest	267

Shell Oil tragedy with the drowning of five men in the Nodwell	272

Learning Instrument Flight Rules the Hard Way	276

Refurbishing The Aeronca 15ac Sedan	285

Flight from Fort McPherson to Coppermine	290

Search For Overdue Canoeists	295

Recover of Bodies In The Open Ocean.	304

Aircraft of Tundra	308

Flight from Coppermine To Grande Prairie	335

Halloween in Grande Prairie, 1971	341

Dog Teams Vs. Ski-Doos	345

My Help Building of Our House	354

Injury Accident in 1973 near Hythe, Alberta	364

Some of the Odd Stories	369

Search for the missing Prospectors	382

Assisting the Mining Recorder	391

Diving on The Pirate Ship in Ferryland Harbour	403

Scuba Diving – (Self Contained Breathing Apparatus)	409

Deepest dive with perfect visibility	420

Stories related to My Carcross Posting	427

Trip to the Engineer Gold Mine	438

Tagish Grave Sites	446

1987 Edmonton Tornado – F4 Tornado – Black Friday	456

Auxillary Constable Program	471
