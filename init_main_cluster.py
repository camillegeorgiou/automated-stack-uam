from elasticsearch import Elasticsearch
import json
from jinja2 import Template

def setup_main_cluster(config):
    es = Elasticsearch(cloud_id=config['main_cluster']['cloud_id'], api_key=config['main_cluster']['api_key'])

    # Create ingest pipeline
    with open('_meta/main_cluster/ingest-pipeline.json') as f:
        pipeline_body = json.load(f)
    es.ingest.put_pipeline(id="kibana-objectid", body=pipeline_body)
    print("Ingest pipeline created in main cluster.")
    
    # Create component template
    with open('_meta/main_cluster/component-template.json') as f:
        template_body = json.load(f)
    es.cluster.put_component_template(name="kibana-objects", body=template_body)
    print("Component template created in main cluster.")

    # Create index template
    with open('_meta/main_cluster/index-template.json') as f:
        template_body = json.load(f)
    es.indices.put_index_template(name="kibana_objects-new", body=template_body)
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
    es = Elasticsearch(cloud_id=config['main_cluster']['cloud_id'], api_key=config['main_cluster']['api_key'])

    with open(watcher_template_path, 'r') as file:
        template_content = file.read()

    template = Template(template_content)
    watcher_config_str = template.render(host=config['watcher_main']['host'], api_key=config['watcher_main']['api_key'])

    watcher_config = json.loads(watcher_config_str)
    es.watcher.put_watch(id="kibana-reindex", body=watcher_config)
    print("Watcher setup in main cluster.")
