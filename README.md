# NLP For SEC

This repo contains scripts and programs for the exploration of NLP/ML for the SEC project.

## Production

### Deploying Code to Production

1. Push changes to main branch.
2. Log in to the remote server with your NIH credentials.
3. Authenticate to GitHub with `gh auth login`.
4. Obtain `shiny` access with `sudo su shiny`.
5. Navigate to the shiny NLP bin folder `~/bin/nlp_pg`.
6. Make sure the current branch is set to `main`.
7. Create a commit checkpoint with `git tag save-point`.
8. Run `git pull` to get the latest changes from `main`.
9. If everything looks good, delete the checkpoint tag `git tag -d save-point`. **You're done.**
10. If there's an error with the new changes, you can quickly restore the last working version with `git reset --hard save-point`.
11. Fix the issue, apply the changes to main, repeat the process.
