import sys
import os
import time
import datetime
import argparse
import errno
import yaml
from pprint import pprint
import FACTS as facts
from radical.entk import AppManager
import json


def run_experiment(exp_dir, debug_mode = False, alt_id = False, resourcedir = None, makeshellscript = False, globalopts = None):

    if not resourcedir:
        resourcedir = exp_dir

    expconfig = facts.ParseExperimentConfig(exp_dir, globalopts=globalopts)
    experimentsteps = expconfig['experimentsteps']
    workflows = expconfig['workflows']
    climate_data_files = expconfig['climate_data_files']

    # write workflows to yml file
    f = open(os.path.join(exp_dir, 'workflows.yml'), 'w')
    f.write("# automatically generated by runFACTS.py\n")
    f.write("#\n")
    yaml.dump(workflows, f)
    f.close()

    # write location file if none exists
    if not os.path.isfile(os.path.join(exp_dir, "location.lst")):
        with open(os.path.join(exp_dir, "location.lst"), 'w') as templocationfile:
            templocationfile.write("New_York\t12\t40.70\t-74.01")

    # Print out PST info if in debug mode
    if debug_mode:
        print_experimentsteps(experimentsteps)
        print('')
        print('CLIMATE DATA')
        print('------------')
        pprint(climate_data_files)
        print('')
        print_workflows(workflows)
        # Exit
        sys.exit(0)

    # Print out shell script if in shell script mode
    if makeshellscript:
        print_experimentsteps_script(experimentsteps, exp_dir=exp_dir)
        sys.exit(0)

    # Does the output directory exist? If not, make it
    try:
        os.makedirs(os.path.join(exp_dir, "output"))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    # Apply the resource configuration provided by the user
    rcfg_name = expconfig['ecfg']['global-options'].get('rcfg-name')
    rcfg = facts.LoadResourceConfig(resourcedir, rcfg_name)

    # Initialize RCT and the EnTK App Manager
    if 'mongodb_url' in rcfg:
        dburl = rcfg['mongodb_url']
    elif not "mongodb" in rcfg.keys():
        dburl = 'mongodb://localhost:27017/facts'
    elif not "password" in rcfg['mongodb'].keys():
        dburl = 'mongodb://%s:%d/facts' % (rcfg['mongodb'].get('hostname', 'localhost'), rcfg['mongodb'].get('port', 27017))
    else:
        dburl = 'mongodb://%s:%s@%s:%d/facts' \
                % (rcfg['mongodb'].get('username', ''),
                rcfg['mongodb'].get('password', ''),
                rcfg['mongodb'].get('hostname', 'localhost'),
                rcfg['mongodb'].get('port', 27017))
    os.environ['RADICAL_PILOT_DBURL'] = dburl

    if not "rabbitmq" in rcfg.keys():
        # we may be running the development version of radical.entk that doesn't require RabbitMQ
        #amgr = AppManager(autoterminate=False)
        if alt_id:
            date_now = datetime.datetime.now().strftime('%m%d%Y.%I%M%S%p').lower()
            exp_name = os.path.basename(os.path.normpath(exp_dir))
            session_name = f'facts.{rcfg_name}.{str(exp_name).lower()}.{date_now}'
            amgr = AppManager(name=session_name,autoterminate=False)
        # retains the original naming convention from RCT
        else:
            amgr = AppManager(autoterminate=False)    
    else:
        if not "password" in rcfg['rabbitmq'].keys():
            amgr = AppManager(hostname=rcfg['rabbitmq'].get('hostname', ''),
                        port=rcfg['rabbitmq'].get('port', 5672),
                        autoterminate=False)
        else:
            amgr = AppManager(hostname=rcfg['rabbitmq'].get('hostname', ''),
                        username=rcfg['rabbitmq'].get('username', ''),
                        password=rcfg['rabbitmq'].get('password', ''),
                        port=rcfg['rabbitmq'].get('port', 5672),
                        autoterminate=False)

    amgr.resource_desc = rcfg['resource-desc']

    # Load the localization list
    amgr.shared_data = [os.path.join(exp_dir, "location.lst")]

    for step, pipelines in experimentsteps.items():

        print ("****** STEP: " + step + " ******")
        # Assign the list of pipelines to the workflow
        amgr.workflow = pipelines

        # Run the SLR projection workflow
        amgr.run()

    # Close the application manager
    amgr.terminate()

def print_workflows(workflows):

    for this_workflow in workflows:
        print('WORKFLOW: ', this_workflow)
        print('-----------------')
        pprint(workflows[this_workflow])
        print('')


def print_pipeline(pipelines):

    for p in pipelines:
        print("Pipeline {}:".format(p.name))
        print("################################")
        print(p.as_dict())
        for s in p.stages:
            print("Stage {}:".format(s.name))
            print("============================")
            pprint(s.as_dict())
            for t in s.tasks:
                print("Task {}:".format(t.name))
                print("----------------------------")
                pprint(t.as_dict())


def print_experimentsteps(experimentsteps):

    for this_step, pipelines in experimentsteps.items():
        print('EXPERIMENT STEP: ', this_step)
        print('-----------------')
        print_pipeline(pipelines)
        print('')

def print_experimentsteps_script(experimentsteps, exp_dir = None):

    print('#!/bin/bash\n')

    print('if [ -z "$WORKDIR" ]; then  ')
    print('   WORKDIR=/scratch/`whoami`/test.`date +%s`')
    print('fi')
    print('mkdir -p $WORKDIR\n')
    print('if [ -z "$OUTPUTDIR" ]; then  ')
    print('   OUTPUTDIR=/scratch/`whoami`/test.`date +%s`/output')
    print('fi')
    print('mkdir -p $OUTPUTDIR')
    print('BASEDIR=`pwd`')

    for this_step, pipelines in experimentsteps.items():
        print('\n#EXPERIMENT STEP: ', this_step, '\n')
        for p in pipelines:
            print("\n# - Pipeline {}:\n\n".format(p.name))
            print("PIPELINEDIR=$WORKDIR/{}".format(p.name))
            print('mkdir -p $PIPELINEDIR\n')
            print('cd $BASEDIR')
            if len(exp_dir)>0:
                print("cp {}/location.lst $PIPELINEDIR".format(exp_dir))
            for s in p.stages:
                print("\n# ---- Stage {}:\n".format(s.name))
                for t in s.tasks:
                    tdict = t.as_dict()
                    print('cd $BASEDIR')
                    if 'upload_input_data' in tdict.keys():
                        if len(tdict['upload_input_data']) > 0:
                            print('cp ' + ' '.join(map(str,t['upload_input_data'])) + ' $PIPELINEDIR')
                    #if 'copy_input_data' in tdict.keys():

                    print('cd $PIPELINEDIR')

                    if 'pre_exec' in tdict.keys():
                        print('\n'.join(map(str,t['pre_exec'])))
                    if 'arguments' in tdict.keys():
                        print(tdict['executable'] + ' ' + ' '.join(map(str, t['arguments'])))
                    if 'post_exec' in tdict.keys():
                        print('\n'.join(map(str,t['post_exec'])))
                    #if 'copy_output_data' in tdict.keys():
                    if 'download_output_data' in tdict.keys():
                        for df in tdict['download_output_data']:
                            ddf = df.split(' ')
                            print('cp ' + ddf[0] + ' $OUTPUTDIR' )

if __name__ == "__main__":

    # Initialize the argument parser
    parser = argparse.ArgumentParser(description="The Framework for Assessing Changes To Sea-level (FACTS)")

    # Add arguments for the resource and experiment configuration files
    parser.add_argument('edir', help="Experiment Directory")
    parser.add_argument('--shellscript', help="Turn experiment config into a shell script (only limited file handling, works best with single-module experiments)", action="store_true")
    parser.add_argument('--debug', help="Enable debug mode (check that configuration files parse, do not execute)", action="store_true")
    parser.add_argument('--resourcedir', help="Directory containing resource files (default=./resources/)", type=str, default='./resources')
    parser.add_argument('--alt_id', help='If flagged, then the session ID will be in the format EXPNAME.MMDDYYY.HHMMSS', action='store_true')
    parser.add_argument('--global_options', help='Dictionary of global options to overwrite those specified in config.tml', type=json.loads)

    # Parse the arguments
    args = parser.parse_args()
 
    # Does the experiment directory exist?
    if not os.path.isdir(args.edir):
        print('{0} does not exist'.format(args.edir))
        sys.exit(1)

    # Go ahead and try to run the experiment
    run_experiment(args.edir, args.debug, args.alt_id, resourcedir=args.resourcedir, makeshellscript = args.shellscript, globalopts = args.global_options)

    #sys.exit(0)
