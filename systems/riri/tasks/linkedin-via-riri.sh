#!/usr/bin/env bash
# This is how LinkedIn posting SHOULD be dispatched:
# RiRi receives the task → passes to browser-use agent → browser-use does the work

TASK="Go to https://www.linkedin.com/feed/ using the browser.
Click 'Start a post'.
Type the following post exactly:

$(cat ~/projects/riri/tasks/linkedin-draft.txt)

Click the Post button. Take a screenshot when done and save it to ~/Desktop/case-studies/linkedin-screenshot.png."

# Pass to browser-use agent (runs headful on DISPLAY=:1 so Ahmed can watch)
DISPLAY=:1 browser-use "$TASK"
