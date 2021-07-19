#!/usr/bin/env python3
import dnf
# Generate workflows for nginx/module/branch/release that are missing from the repo
# 1. read each.yml for info on release (default 1 if not specified), excluded/included branches for it
# 2. for each "build" of the module, check against corresponding repo whether we already have this version/release built
# 3. if not, create workflow for it
# this is good as replacement to our daily cron

# if many modules, batch their deploy somehow
base = dnf.Base()
conf = base.conf
# base.read_all_repos()
repos = {
    'el7-master': 'https://extras.getpagespeed.com/redhat/7/x86_64/'
}
for k, r in repos.items():
    base.repos.add_new_repo(k, conf, baseurl=[r])
base.fill_sack()

q = base.sack.query()
i = q.available()
i = i.filter(name='nginx-module-brotli').latest()

ps = i.run()
print(ps[0].version)