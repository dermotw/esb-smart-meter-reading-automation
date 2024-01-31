Forked from https://github.com/badger707/esb-smart-meter-reading-automation

Modified so that values are added to an InfluxDB (version 2+).

Copy `config.yml.example` to `config.yml`, update the parameters and then run the script.

It's a bit of a ball-ache because the ESB API ignores the startDate and downloads multiple years worth of data every time you run it. If I have a TODO list for this, it's probably to add an option that skips any row in the CSV that's older than 1 week.
