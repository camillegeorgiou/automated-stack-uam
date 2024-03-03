from elasticsearch import Elasticsearch
import json
from jinja2 import Template

def setup_main_cluster(config):
    es = Elasticsearch(cloud_id=config['main_cluster']['cloud_id'], api_key=config['main_cluster']['api_key'])

    # Create ingest pipeline if not exists
    pipeline_id = "kibana-objectid"
    if pipeline_exists(es, pipeline_id):
        print("Ingest pipeline already exists in main cluster.")
    else:
        with open('_meta/main_cluster/ingest-pipeline.json') as f:
            pipeline_body = json.load(f)
        es.ingest.put_pipeline(id=pipeline_id, body=pipeline_body)
        print("Ingest pipeline created in main cluster.")
    
    # Create component template if not exists
    component_template_name = "kibana-objects"
    if component_template_exists(es, component_template_name):
        print("Component template already exists in main cluster.")
    else:
        with open('_meta/main_cluster/component-template.json') as f:
            template_body = json.load(f)
        es.cluster.put_component_template(name=component_template_name, body=template_body)
        print("Component template created in main cluster.")

    # Create index template if not exists
    index_template_name = "kibana_objects-new"
    if index_template_exists(es, index_template_name):
        print("Index template already exists in main cluster.")
    else:
        with open('_meta/main_cluster/index-template.json') as f:
            template_body = json.load(f)
        es.indices.put_index_template(name=index_template_name, body=template_body)
        print("Index template created in main cluster.")

    # Set-up reindex
    with open('_meta/main_cluster/reindex.json') as f:
        reindex_body = json.load(f)
    es.reindex(body=reindex_body)
    print("Data reindexed.")

    # Set-up watcher in mon cluster
    setup_watcher_with_jinja(es, config, '_meta/main_cluster/watcher.json')

    return es

def setup_watcher_with_jinja(es, config, watcher_template_path):
    watcher_id = "kibana-reindex"
    if watcher_exists(es, watcher_id):
        print("Watcher already exists in main cluster.")
    else:
        with open(watcher_template_path, 'r') as file:
            template_content = file.read()

        template = Template(template_content)
        watcher_config_str = template.render(host=config['watcher_main']['host'], api_key=config['watcher_main']['api_key'])

        watcher_config = json.loads(watcher_config_str)
        es.watcher.put_watch(id=watcher_id, body=watcher_config)
        print("Watcher setup in main cluster.")

def pipeline_exists(es, pipeline_id):
    try:
        es.ingest.get_pipeline(id=pipeline_id)
        return True
    except Exception as e:
        return False

def component_template_exists(es, component_template_name):
    try:
        es.cluster.get_component_template(name=component_template_name)
        return True
    except Exception as e:
        return False

def index_template_exists(es, index_template_name):
    try:
        es.indices.get_index_template(name=index_template_name)
        return True
    except Exception as e:
        return False

def watcher_exists(es, watcher_id):
    try:
        es.watcher.get_watch(id=watcher_id)
        return True
    except Exception as e:
        return False
