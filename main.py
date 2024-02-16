import json
from init_main_cluster import setup_main_cluster
from init_monitoring_cluster import setup_monitoring_cluster

def load_config():
    with open('clusters_config.json') as f:
        return json.load(f)    

def main():
    config = load_config()
    
    # Setup main cluster and monitoring cluster
    
    setup_main_cluster(config) 
    setup_monitoring_cluster(config)

if __name__ == "__main__":
    main()
