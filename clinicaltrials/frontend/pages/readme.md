## This is a sample static page

Files with the extension `.md`, placed in this folder, will appear on
the website under https://fdaaa.trialstracker.net/pages/ (but without
the `.md` extension).  For example, this file you're looking at now
appears at https://fdaaa.trialstracker.net/pages/readme

You can create subdirectories too, so a file at
`clinicaltrials/frontend/pages/faqs/what_is_a_fogou.md` will appear at
https://fdaaa.trialstracker.net/pages/what_is_a_fogou.  The page title
is taken from the filename, so in this example the page title would be
"What Is A Fogou".

These files are formatted
using
[markdown](https://guides.github.com/features/mastering-markdown/).

There is one special category of page. Any page in the folder at
`clinicaltrials/frontend/pages/trials/` with a name matching a trial
registry ID will automatically included in its corresponding trial
page. For example, a file at
`clinicaltrials/frontend/pages/trials/NCT00879437.md` would be
included at the bottom of the trial page at
https://fdaaa.trialstracker.net/trial/NCT00879437/.

If that page includes a horizontal rule (`----` in markdown), then
only the text above the rule will be included on the trial page,
followed by a link to the full page.
