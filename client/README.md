# giza-website-2019

Pixels for Humans front-end for the Digital Giza Project website, based on the [Foundation for Sites](http://foundation.zurb.com/sites) framework created by ZURB.

Note: Currently uses Foundation for Sites version 6.2.4 (not the latest). [Docs are here](https://foundation.zurb.com/sites/docs/), [changelog is here](https://github.com/zurb/foundation-sites/releases/). This site also relies on some libraries that have since been deprecated, such as Bower. Migration to a newer version of Foundation, and migration away from those libraries, is unlikely in the short term.  

## Setup instructions for local development

Please see the prerequisites you need, in the Foundation README below under "Installation."

1. Clone the repo locally.
2. In a terminal window, `cd` to the local folder and run `npm install`.
3. You may also need to run `bower install` to grab the front-end dependencies.
4. To preview on localhost with Gulp, run `npm start`. The site will open at `http://localhost:8000`.

## Git branch structure

We use a simple version of the [Git Flow workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow) to manage version control on this project. In short: we don't update `master` that much (only for official releases); we use a `develop` branch to track the full commit history of the project; and we create a feature branch off of `develop` for any change we make.

We also use SourceTree as a GUI for version control, but feel free to use the command line instead. 

Please be sure to do the following after your initial setup of the repo locally:

1. Double-check with `git status` what branch you've checked out by default - probably `master`.
2. Checkout branch `develop` instead.
3. When you're ready to start working, create a new branch off of `develop`. Name your branch with your initials, then something brief and descriptive about the feature you're developing. So for example, `jo-mygiza-integration` or whatever.
4. When you're done developing your feature, probably check with Jim first, but you should be able to just merge your feature branch back into `develop`. Please don't touch `master` without an explicit green light from Jim.

## Where stuff lives

Foundation uses Handlebars-style templating, so that reusable partials can be included in other files. This makes the file structure a bit opaque at first.

* The basic HTML shell is in `src/layouts/default.html`
* Markup for full pages is in `src/pages`
* Markup for smaller reusable partials is in `src/partials`
* Sass files are in `src/assets/scss`. All custom stuff is divided into Sass partials in `src/assets/scss/components`.

## Build notes

Gulpfile has been customized to accommodate webroot assets - things like favicons - 
which can be placed in `src/assets/root` and will be moved into the `dist` folder 
(root level) during each build.


----

Foundation for Sites README content below.


# ZURB Template

[![devDependency Status](https://david-dm.org/zurb/foundation-zurb-template/dev-status.svg)](https://david-dm.org/zurb/foundation-zurb-template#info=devDependencies)

**Please open all issues with this template on the main [Foundation for Sites](https://github.com/zurb/foundation-sites/issues) repo.**

This is the official ZURB Template for use with [Foundation for Sites](http://foundation.zurb.com/sites). We use this template at ZURB to deliver static code to our clients. It has a Gulp-powered build system with these features:

- Handlebars HTML templates with Panini
- Sass compilation and prefixing
- JavaScript concatenation
- Built-in BrowserSync server
- For production builds:
  - CSS compression
  - JavaScript compression
  - Image compression

## Installation

To use this template, your computer needs:

- [NodeJS](https://nodejs.org/en/) (0.12 or greater)
- [Git](https://git-scm.com/)

This template can be installed with the Foundation CLI, or downloaded and set up manually.

### Using the CLI

Install the Foundation CLI with this command:

```bash
npm install foundation-cli --global
```

Use this command to set up a blank Foundation for Sites project with this template:

```bash
foundation new --framework sites --template zurb
```

The CLI will prompt you to give your project a name. The template will be downloaded into a folder with this name.

### Manual Setup

To manually set up the template, first download it with Git:

```bash
git clone https://github.com/zurb/foundation-zurb-template projectname
```

Then open the folder in your command line, and install the needed dependencies:

```bash
cd projectname
npm install
bower install
```

Finally, run `npm start` to run Gulp. Your finished site will be created in a folder called `dist`, viewable at this URL:

```
http://localhost:8000
```

To create compressed, production-ready assets, run `npm run build`.

