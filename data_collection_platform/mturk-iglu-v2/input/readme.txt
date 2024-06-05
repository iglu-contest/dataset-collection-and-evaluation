The folder contains the following templates for HITs and Qualification Types:

For the role Architect:

HITs:
architect-answer-cq.xml -> Template for the HIT where Architect needs to answer the clarifying question (cq)
   INPUT VAR:
   -$gameId - (part of the URL) id of the game needed to retrieve target structure views
   -$screenshotId - (part of the URL) needed to retrieve screenshots location from the previous builder move. the expected end of the URL is `view-west/east/south/north.png'
   -$previousInstr - instruction that the previous builder has questioned
   -$screenshotView - screenshot view that the previous instruction has been assigned to
   -$question - the clarifying question

architect-initial.xml   -> Template for the initial (first) HIT where Architect needs to give the first instruction
   INPUT VAR: 
   -$gameId - (as above)

architect-normal.xml    -> Template for the situation where Architect needs to pick a view and give the instruction based on this view
   INPUT VAR:
   - $gameId - (as above)
   -$screenshotView - (as above)

QualificationType:
architect-qualification-answers.xml   -> answers for the qualification test. all four should be correct to qualify 
architect-qualification-questions.xml -> questions for qualification test.


For the role Builder:

HITs:
builder-answer-cq.xml 
builder-initial.xml
builder-normal.xml

QualificationType:
builder-qualification-answers.xml
builder-qualification-questions.xml