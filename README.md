SamAware
========

SamAware is a [pretalx](https://pretalx.com/) plugin with enhanced features for speaker care during a conference.

It is designed for conference staff taking care of speaker check-in, talk assistance, program coordination, stage operations, and similar tasks.
SamAware was originally developed for the Speakers' Desk at [Chaos Communication Congress](https://en.wikipedia.org/wiki/Chaos_Communication_Congress).

<img src="src/samaware/static/samaware/samovar.svg" alt="Stylized black and white icon of a Samovar tea pot" width="200" />

## Features

SamAware enhances the pretalx orga interface with these features:

- Dashboard with at-a-glance stats on missing speakers, unreleased schedule changes, etc.
- Incremental search for talks by title or speaker name
- Overview page for each talk gathering the relevant submission and speaker information
- List of talks with "Don't record" setting
- Tech Riders for talks with special technical requirements
- Optional sync of the Tech Riders to a [Wekan](https://wekan.fi/) board *(error-prone, to be replaced with sync to another ticket system)*
- Speaker Care Messages with internal information on a speaker that will be displayed prominently when accessing them or their talks

## Installation

> [!WARNING]
> Due to [backward-incompatible changes in django-csp 4](https://django-csp.readthedocs.io/en/latest/migration-guide.html), SamAware is currently not compatible with any released pretalx version, but only the current development version from Git.
> This is going to change with the next pretalx release.

SamAware is available from PyPI and gets installed like any other pretalx plugin.
First, install the package into your pretalx installation's Python environment:

    (env) > pip install samaware

Next, you need to collect and compress static assets:

    (env) > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin collectstatic
    (env) > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin compress

Afterward, restart pretalx.

SamAware should now appear in the pretalx orga interface of your Event under "Settings" / "Plugins" / "Features".
You can enable it there for each Event.

SamAware requires no configuration unless you plan to use Wekan sync of Tech Riders.
For that feature, provide the required information under "Settings" / "SamAware".

## Development

For a local development environment, set up a [Python venv](https://docs.python.org/3/library/venv.html) or use a dev container.

pretalx itself must be installed in that environment.
One option is to create a full development setup as described [in the pretalx docs](https://docs.pretalx.org/developer/setup/).
Alternatively, you can get the latest pretalx release from PyPI by running:

    > pip install pretalx

In both cases, you then clone the SamAware repo, change to that source directory, and add it to your environment like this:

    > pip install -e .[dev]

You probably need to collect and compress static assets and apply migrations:

    > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin collectstatic
    > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin compress
    > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin migrate

If not done already, initialize your pretalx dev instance through:

    > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin init

It is useful to create a demo Event for development.
This requires the "Faker" and "freezegun" Python packages.
Setting it up in the "schedule" stage provides the best starting point for SamAware development:

    > pip install Faker freezegun
    > DJANGO_SETTINGS_MODULE=pretalx.settings django-admin create_test_event --stage schedule

Now, you should be able to start the development server through:

    make run

Make sure to have a look at the Makefile as it also provides useful targets for testing and linting.

Finally, open the running instance in a browser and enable SamAware in the orga interface for your demo Event under "Settings" / "Plugins" / "Features".

## Security

Should you encounter any security vulnerabilities in SamAware, please report them privately.
Use GitHub vulnerability reporting or contact Felix Dreissig directly.

## Copyright

SamAware has been created by Felix Dreissig.

It is released under the ISC License.
