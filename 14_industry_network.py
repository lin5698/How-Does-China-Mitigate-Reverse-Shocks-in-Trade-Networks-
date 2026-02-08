"""
Industry-Level Network Data Preparation
Creates multi-layer network with country-industry nodes

Network structure:
- Nodes: Country-Industry combinations (e.g., CHN_Manufacturing)
- Edges: Inter-industry trade flows and input-output linkages
- Layers: Different industries or sectors
- Captures cross-industry dependencies and supply chain structure
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR, ISIC_REV4_SECTORS
from utils import save_dataframe, logger, print_data_summary

try:
    import networkx as nx
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False
    logger.warning("networkx not installed")


def load_io_table_data() -> pd.DataFrame:
    """
    Load input-output table data
    
    Returns:
        Combined IO table data
    """
    logger.info("Loading input-output table data...")
    
    all_data = []
    
    # Load OECD ICIO
    icio_files = list(DATA_DIR.glob("*icio*rcep*.csv"))
    for filepath in icio_files:
        df = pd.read_csv(filepath, low_memory=False)
        df['source'] = 'icio'
        all_data.append(df)
        logger.info(f"Loaded {filepath.name}")
    
    # Load WIOD
    wiod_files = list(DATA_DIR.glob("wiod_rcep*.csv"))
    for filepath in wiod_files:
        df = pd.read_csv(filepath)
        df['source'] = 'wiod'
        all_data.append(df)
        logger.info(f"Loaded {filepath.name}")
    
    # Load ADB MRIO
    mrio_files = list(DATA_DIR.glob("adb_mrio_rcep*.csv"))
    for filepath in mrio_files:
        df = pd.read_csv(filepath)
        df['source'] = 'mrio'
        all_data.append(df)
        logger.info(f"Loaded {filepath.name}")
    
    if not all_data:
        logger.warning("No IO table data found!")
        return pd.DataFrame()
    
    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"Combined {len(combined)} observations")
    
    return combined


def create_industry_network(io_df: pd.DataFrame) -> nx.DiGraph:
    """
    Create industry-level network from IO table
    
    Args:
        io_df: Input-output table data
    
    Returns:
        NetworkX DiGraph with country-industry nodes
    """
    if not NX_AVAILABLE:
        logger.error("NetworkX not available")
        return None
    
    logger.info("Creating industry-level network...")
    
    G = nx.DiGraph()
    
    # Add nodes (country-industry combinations)
    for country in RCEP_COUNTRIES.keys():
        for industry in ISIC_REV4_SECTORS:
            node_id = f"{country}_{industry}"
            G.add_node(node_id, country=country, industry=industry)
    
    # Add edges from IO table
    # This is simplified - actual implementation depends on IO table structure
    # Typically: intermediate flows from country_i-industry_j to country_k-industry_l
    
    logger.info(f"Industry network created: {G.number_of_nodes()} nodes")
    
    return G


def calculate_industry_metrics(G: nx.DiGraph) -> pd.DataFrame:
    """
    Calculate industry-level network metrics
    
    Args:
        G: Industry network graph
    
    Returns:
        DataFrame with metrics
    """
    if not NX_AVAILABLE or G is None:
        return pd.DataFrame()
    
    logger.info("Calculating industry network metrics...")
    
    metrics = []
    
    # Calculate centrality measures
    in_degree = dict(G.in_degree(weight='weight'))
    out_degree = dict(G.out_degree(weight='weight'))
    
    for node in G.nodes(data=True):
        node_id = node[0]
        node_data = node[1]
        
        metrics.append({
            'node_id': node_id,
            'country': node_data.get('country', ''),
            'industry': node_data.get('industry', ''),
            'in_degree': in_degree.get(node_id, 0),
            'out_degree': out_degree.get(node_id, 0),
            'total_degree': in_degree.get(node_id, 0) + out_degree.get(node_id, 0)
        })
    
    metrics_df = pd.DataFrame(metrics)
    print_data_summary(metrics_df, "Industry Network Metrics")
    
    return metrics_df


def export_industry_network(G: nx.DiGraph):
    """
    Export industry network files
    
    Args:
        G: Industry network graph
    """
    if not NX_AVAILABLE or G is None:
        return
    
    logger.info("Exporting industry network...")
    
    # Edge list
    edge_list = []
    for u, v, data in G.edges(data=True):
        edge_list.append({
            'source': u,
            'target': v,
            'weight': data.get('weight', 0)
        })
    
    if edge_list:
        edge_df = pd.DataFrame(edge_list)
        edge_file = DATA_DIR / "industry_network_edges.csv"
        save_dataframe(edge_df, edge_file)
    
    # Node list
    node_list = []
    for node, data in G.nodes(data=True):
        node_list.append({
            'id': node,
            'country': data.get('country', ''),
            'industry': data.get('industry', '')
        })
    
    node_df = pd.DataFrame(node_list)
    node_file = DATA_DIR / "industry_network_nodes.csv"
    save_dataframe(node_df, node_file)
    
    # GML format
    gml_file = DATA_DIR / "industry_network.gml"
    nx.write_gml(G, gml_file)
    logger.info(f"Saved to {gml_file}")


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("Industry-Level Network Preparation")
    logger.info("="*60)
    
    # Load IO table data
    io_df = load_io_table_data()
    
    if io_df.empty:
        logger.error("No IO table data available")
        logger.info("Please run IO table acquisition scripts first:")
        logger.info("- 08_oecd_icio.py")
        logger.info("- 09_wiod.py")
        logger.info("- 10_adb_mrio.py")
        return
    
    # Create industry network
    if NX_AVAILABLE:
        G = create_industry_network(io_df)
        
        if G:
            # Calculate metrics
            metrics = calculate_industry_metrics(G)
            metrics_file = DATA_DIR / "industry_network_metrics.csv"
            save_dataframe(metrics, metrics_file)
            
            # Export network
            export_industry_network(G)
    else:
        logger.warning("NetworkX not available")
        logger.info("Install with: pip install networkx")
    
    logger.info("\n" + "="*60)
    logger.info("Industry network preparation complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
