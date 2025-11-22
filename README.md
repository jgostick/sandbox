# `bump-my-version` Sandbox
I created this repo so I could experiment with the settings of the [bump-my-version](https://callowayproject.github.io/bump-my-version/) package. This package is now used in the Github Actions workflows of [OpenPNM](http://openpnm.org) to manage the version changes each time a PR is merged into the `dev` and `release` branch. Through my playing with the present repo I was able to get the workflow in good shape and thought I'd capture that info here.

1. Firstly, the `bump-my-version` package is relatively new (actually a rewrite of an older package called `bump-2-version` which we used to use), so it is able to look into the [pyproject.toml](https://github.com/jgostick/bump-my-version-sandbox/blob/dev/pyproject.toml) file to retrieve its settings. The following are the settings we landed on, which are basically the default ones, with a few expections which I will point out. To get things started you must enter your version in the `current_version` field, and it will increment from that.  Also note that the official package `version` is written with the same value. I'm not sure if the `current_version` is really necessary since the official version is also given, but it's not a problem since `bump-my-version` will increment both of these. 

```toml
[project]
name = "bump-my-version-sandbox"

version = "1.1.0-dev1"
requires-python = "<3.13"
dependencies = []

[tool.bumpversion]
current_version = "1.1.0-dev1"
parse = """(?x)
    (?P<major>0|[1-9]\\d*)\\.
    (?P<minor>0|[1-9]\\d*)\\.
    (?P<patch>0|[1-9]\\d*)
    (?:
        -                             # dash separator for pre-release section
        (?P<pre_l>[a-zA-Z-]+)         # pre-release label
        (?P<pre_n>0|[1-9]\\d*)        # pre-release version number
    )?                                # pre-release section is optional
"""
serialize = [
    "{major}.{minor}.{patch}-{pre_l}{pre_n}",
    "{major}.{minor}.{patch}",
]
search = "{current_version}"
replace = "{new_version}"
regex = false
ignore_missing_version = false
tag = true
sign_tags = false
tag_name = "v{new_version}"
tag_message = "Bump version: {current_version} → {new_version}"
allow_dirty = false
commit = false
message = "Bump version: {current_version} → {new_version}"
commit_args = ""

[tool.bumpversion.parts.pre_l]
values = ["dev", "rc", "final"]
optional_value = "dev"
```
   
2. There are two Github Action workflows:
   -  [bump-version-dev.yml](https://github.com/jgostick/bump-my-version-sandbox/blob/dev/.github/workflows/bump-version-dev.yml)
   -  [bump-version-release.yml](https://github.com/jgostick/bump-my-version-sandbox/blob/dev/.github/workflows/bump-version-release.yml)
   These are trigged by pushes to the `dev` branch and `release` branch via the following bits:

```yaml
on:
  push:
    branches:
      - dev  # or release
```

3. When a PR is merged into `dev`, the `bump-version-dev` workflow is triggered, and will automatically update the version from `a.b.c-devX` to `a.b.c-devY`. We like having the `-devN` suffix so we know how far ahead the `dev` branch is over the `release` branch. The `N` tells us directly how many changes have been made to `dev`. `bump-my-version` has the ability to probe the git history and count the total number of commits, but the simple count approach basically tells how many PRs have been merged (assuming no direct pushed to `dev`) which is good enough. Note that `rc` and `final` suffix labels are defined but our workflows dont' use these at the moment. 
4. When `dev` is merged into `release` the `bump-version-release` action is triggered which will increment either the `major`, `minor` or `patch` version number and drop the `-devN` suffix. For example if doing a minor release the version number will go from `a.b.c-devN` to `a.c.a`.  The way that we specify a `major`, `minor` or `patch` release is via the merge message.  Github can scan the message text and look for `#major`, `#minor` or `#patch` (`if: contains(github.event.head_commit.message, '#patch'`).  There are if-statements in the `bump-version-release.yml` file which will call the corresponding command. For instance, if the merge message contains `#patch` then `bump-my-version bump patch` is called, as shown below:

```yaml
- name: Bump version (patch)
  if: contains(github.event.head_commit.message, '#patch')
  run: |
    bump-my-version bump patch --commit --message "Bump version number on release"
    git push origin HEAD:release
    git push --tags
```

I think it is possible for the `#patch` tag to be caught in a variable then passed to the `bump` command like `bump-my-version $VAR`, avoiding the need to have if-statements for each case, but I didn't want to invest time figuring this out, and it would make the workflow harder to understand later anyway.

5. We also want to the version to be embedded in a tag on the git repo. In the `pyproject.toml` file we have set `tag = true`, so when `bump-my-version` runs it creates a tag with the current version number.  It took me a while to figure out how to put the tag and the version number change on the same commit. Our workflows previously used an action for committing changes, which was the problem.  Once I switched to the `git push origin HEAD:release` and `git push --tags` things worked great.
  
6. There were a few additional considerations too.  When installing the `bump-my-version` I thought it would be smart to specify a version so that the developers of that package can change their api if they wish without impacting us.  I also learned it was necessary to specify the user info so that `git` could assign an author to the commits:

```yaml
- name: Install dependencies
    run: |
      pip install bump-my-version==1.2.4
      git config --local user.email "action@github.com"
      git config --local user.name "GitHub Action"
```

7. We also need to remember to merge the changed version number from the `release` branch back into the `dev` branch, so the `bump-version-release` has an extra block at the end which creates a PR onto `dev`. The only manual part of this is that we must remember to actually merge the PR before doing any more work on `dev`. 

```yaml
- name: Create Pull Request to merge back release into dev
    uses: repo-sync/pull-request@v2
    with:
      source_branch: "release"                          # If blank, default: triggered branch
      destination_branch: "dev"                         # If blank, default: master
      pr_title: "Merge release branch back into dev"
      pr_body: "Changes made to the release branch (if any), plus the version bump."
      pr_assignee: "jgostick"                           # Comma-separated list (no spaces)
      pr_label: "high priority"                         # Comma-separated list (no spaces)
      pr_draft: false                                   # Creates pull request as draft
      pr_allow_empty: true                              # Creates pull request even if there are no changes
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

> Note that the `repo-sync/pull-request@v2` action has been archived by the authors and they suggest just using the Github CLI commands directly.  In a way I'm glad that this action is archived because it means they won't change something and break our workflow, but I suppose eventually we should migrate to the more modern approach.  

8. And finally, I leared that writing the version to a file in the repo like `_version.py` is no longer necessary. The `version` field in the `pyproject.toml` is the 'canonical/official/blessed' version.  It is used by placing the following code in the package's `__init__.py` file:

```python
import tomllib as _toml

with open("./pyproject.toml", "rb") as f:
    data = _toml.load(f)
    __version__ = data["project"]["version"]
```

This will fetch the version and return it when the user types `<package>.__version__` at the python prompt. One issue I did encounter was that the recommend approach of using the `importlib.metadata` package does not quite work.  For instance, it is suggested to use the following:

```python
import importlib.metadata as _metadata
__version__ = _metadata.version(__package__ or __name__)
```
However, I found that this would not report the `-devN` suffix for some reason.  I got the feeling that it was fetching the version from an older location, perhaps a cached installation. I decided that fetching the value directly from the `pyproject` file using the `toml` library was the way to go since it will always fetch the true value, but to be honest it is a little fragile since it using some path navigation so if something ever gets moved around it would fail.  

## Conclusions
It works great and seems to be simple enough that it might qualify as 'robust', meaning I won't have to keep maintaining this each time some piece gets changed. 
