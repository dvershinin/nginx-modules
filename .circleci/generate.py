#!/usr/bin/env python3
import dnf
import lastversion
import yaml
# Generate workflows for nginx/module/branch/release that are missing from the repo
# 1. read each.yml for info on release (default 1 if not specified), excluded/included branches for it
# 2. for each "build" of the module, check against corresponding repo whether we already have this version/release built
# 3. if not, create workflow for it
# this is good as replacement to our daily cron

# if many modules, batch their deploy somehow
base = dnf.Base()
conf = base.conf
# base.read_all_repos()
repo_base = 'https://extras.getpagespeed.com'
nginx_branches = [
    'stable',
    'mainline',
    'plesk'
]

# TODO use same as buildstrap
distros = {
    'rhel': {
        'dist': 'el',
        'alias': 'redhat',
        'versions': [
            7, 8
        ]
    },
    'amazonlinux': {
        'dist': 'amzn',
        'alias': 'amzn',
        'versions': [
            2
        ]
    }
}

build_jobs = []
modules = {
    'brotli': {
        'repo': 'GetPageSpeed/ngx_brotli'
    }
}

# build up final yml based on header.yml and set up jobs: and workflows:
config = {
    'version': '2.1',
    'jobs': {},
    'workflows': {
        'version': 2
    }
}

with open('header.yml') as f:
    header_config = yaml.safe_load(f)

def create_distro_workflow(v, distro_name, distro_config):
    print(f"Generating {v} for {distro_name}")
    dist = distro_name
    if 'dist' in distro_config:
        dist = distro_config['dist']
    distro_build_job_name = f"{dist}{v}"
    # distro_build_job = header_config['defaults']
    docker_tag_base = distro_name
    if 'docker-tag-base' in distro_config:
        docker_tag_base = distro_config['docker-tag-base']
    docker_image = f'getpagespeed/rpmbuilder:{docker_tag_base}-{v}'
    distro_build_job = header_config['defaults'].copy()
    distro_build_job.update({
        'docker': [{
            'image': docker_image
        }]
    })
    config['jobs'][distro_build_job_name] = distro_build_job

    distro_deploy_job_name = f"deploy-{distro_build_job_name}"
    distro_deploy_job = header_config['deploy'].copy()
    distro_deploy_job['environment'] = {
        'DISTRO': distro_build_job_name
    }
    config['jobs'][distro_deploy_job_name] = distro_deploy_job

    distro_workflow_name = f"build-deploy-{distro_build_job_name}"
    distro_workflow = {'jobs': []}
    distro_workflow['jobs'].append(distro_build_job_name)
    distro_workflow['jobs'].append({
        distro_deploy_job_name: {
            'context': 'org-global',
            'requires': [
                distro_build_job_name
            ]
        }
    })

for branch in nginx_branches:
    nginx_version = lastversion.latest("nginx", major=branch)
    sub = '' if branch == 'stable' else f'/{branch}'
    for distro, dist_config in distros.items():
        package_prefix = ""
        if branch == 'plesk':
            if distro == 'amazonlinux':
                # no Plesk for AmazonLinux
                continue
            package_prefix = "sw-"
        for version in dist_config['versions']:
            repo_uri = distro if 'alias' not in dist_config else dist_config['alias']
            repo_url = f"{repo_base}/{repo_uri}/{version}/{sub}/x86_64"
            base.repos.add_new_repo(f"{distro}-{version}-{branch}", conf, baseurl=[repo_url])
            base.fill_sack()
            for module, module_config in modules.items():
                package_name = f"{package_prefix}nginx-module-{module}"
                latest_module_version = lastversion.latest(module_config['repo'])
                latest_package_version = f"{nginx_version}.{latest_module_version}"
                q = base.sack.query()
                i = q.available()
                i = i.filter(name=package_name).latest()
                packages = i.run()
                if packages:
                    current_package = packages[0]
                    current_package_version = current_package.version.replace('+', '.')
                    if latest_package_version == current_package_version:
                        continue
                print(f"Must build {latest_package_version} for {distro} {version}, branch {branch}")
            base.reset(repos=True, sack=True)



