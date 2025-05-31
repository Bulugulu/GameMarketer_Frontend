#!/usr/bin/env python3
"""
Example integration showing how to use ChromaDB vector search 
in your existing GameMarketer application
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB import GameDataSearchInterface
import streamlit as st

class GameAnalysisAgent:
    """Example agent that uses vector search for game analysis"""
    
    def __init__(self):
        self.search_interface = GameDataSearchInterface()
        
    def analyze_game_theme(self, theme_query: str, game_id: str = None):
        """Analyze how games implement a specific theme"""
        print(f"🎯 Analyzing theme: '{theme_query}'")
        
        # Search for relevant content
        content = self.search_interface.search_all_game_content(
            query=theme_query, 
            limit=10, 
            game_id=game_id
        )
        
        # Process features
        feature_analysis = []
        for feature in content['features']:
            feature_analysis.append({
                'name': feature['name'],
                'relevance': feature['relevance_score'],
                'description': feature['description'][:200] + "..." if len(feature['description']) > 200 else feature['description'],
                'game_id': feature['game_id']
            })
        
        # Process screenshots
        screenshot_analysis = []
        for screenshot in content['screenshots']:
            screenshot_analysis.append({
                'path': screenshot['path'],
                'relevance': screenshot['relevance_score'],
                'caption': screenshot['caption'],
                'game_id': screenshot['game_id']
            })
        
        return {
            'theme': theme_query,
            'features': feature_analysis,
            'screenshots': screenshot_analysis,
            'total_matches': len(feature_analysis) + len(screenshot_analysis)
        }
    
    def find_similar_game_mechanics(self, mechanic_description: str):
        """Find games with similar mechanics"""
        features = self.search_interface.search_game_features(
            query=mechanic_description, 
            limit=15
        )
        
        # Group by game
        games_with_mechanic = {}
        for feature in features:
            game_id = feature['game_id']
            if game_id not in games_with_mechanic:
                games_with_mechanic[game_id] = []
            games_with_mechanic[game_id].append(feature)
        
        return games_with_mechanic
    
    def analyze_ui_patterns(self, ui_query: str):
        """Analyze UI patterns across games"""
        screenshots = self.search_interface.search_game_screenshots(
            query=ui_query, 
            limit=20
        )
        
        ui_patterns = []
        for screenshot in screenshots:
            ui_patterns.append({
                'game_id': screenshot['game_id'],
                'ui_description': screenshot['caption'],
                'relevance': screenshot['relevance_score'],
                'screenshot_path': screenshot['path']
            })
        
        return ui_patterns

def streamlit_example():
    """Example Streamlit integration"""
    st.title("🎮 Game Content Vector Search")
    
    # Initialize search interface (cached in session state)
    if 'search_interface' not in st.session_state:
        with st.spinner("Initializing vector search..."):
            st.session_state.search_interface = GameDataSearchInterface()
    
    # Get database stats
    stats = st.session_state.search_interface.get_database_stats()
    
    with st.sidebar:
        st.header("📊 Database Stats")
        for collection in stats['collections']:
            st.metric(collection['name'], collection['count'])
    
    # Search interface
    search_type = st.selectbox(
        "Search Type",
        ["Features", "Screenshots", "Combined"]
    )
    
    query = st.text_input("Enter your search query:", placeholder="e.g., farming mechanics, combat system, menu design")
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.slider("Max Results", 1, 20, 5)
    with col2:
        game_id = st.text_input("Game ID (optional)", placeholder="Filter by specific game")
    
    if st.button("🔍 Search") and query:
        with st.spinner("Searching..."):
            game_id_filter = game_id if game_id.strip() else None
            
            if search_type == "Features":
                results = st.session_state.search_interface.search_game_features(
                    query, limit, game_id_filter
                )
                display_feature_results(results)
                
            elif search_type == "Screenshots":
                results = st.session_state.search_interface.search_game_screenshots(
                    query, limit, game_id_filter
                )
                display_screenshot_results(results)
                
            else:  # Combined
                results = st.session_state.search_interface.search_all_game_content(
                    query, limit, game_id_filter
                )
                display_combined_results(results)

def display_feature_results(results):
    """Display feature search results in Streamlit"""
    st.subheader(f"🎯 Found {len(results)} Features")
    
    for i, feature in enumerate(results, 1):
        with st.expander(f"{i}. {feature['name']} (Score: {feature['relevance_score']:.3f})"):
            st.write(f"**Game ID:** {feature['game_id']}")
            st.write(f"**Description:** {feature['description']}")
            st.write(f"**Relevance Score:** {feature['relevance_score']:.3f}")

def display_screenshot_results(results):
    """Display screenshot search results in Streamlit"""
    st.subheader(f"📸 Found {len(results)} Screenshots")
    
    for i, screenshot in enumerate(results, 1):
        with st.expander(f"{i}. {screenshot['path']} (Score: {screenshot['relevance_score']:.3f})"):
            st.write(f"**Game ID:** {screenshot['game_id']}")
            st.write(f"**Caption:** {screenshot['caption']}")
            st.write(f"**Path:** {screenshot['path']}")
            st.write(f"**Relevance Score:** {screenshot['relevance_score']:.3f}")

def display_combined_results(results):
    """Display combined search results in Streamlit"""
    features = results['features']
    screenshots = results['screenshots']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🎯 Features ({len(features)})")
        for feature in features:
            with st.expander(f"{feature['name']} ({feature['relevance_score']:.3f})"):
                st.write(feature['description'][:200] + "...")
    
    with col2:
        st.subheader(f"📸 Screenshots ({len(screenshots)})")
        for screenshot in screenshots:
            with st.expander(f"{screenshot['path']} ({screenshot['relevance_score']:.3f})"):
                st.write(screenshot['caption'])

def cli_example():
    """Example command-line usage"""
    print("=== Game Content Analysis Examples ===")
    
    agent = GameAnalysisAgent()
    
    # Example 1: Theme analysis
    print("\n1. Analyzing 'farming and agriculture' theme:")
    theme_analysis = agent.analyze_game_theme("farming agriculture crops planting")
    
    print(f"Found {theme_analysis['total_matches']} total matches:")
    print(f"- {len(theme_analysis['features'])} features")
    print(f"- {len(theme_analysis['screenshots'])} screenshots")
    
    if theme_analysis['features']:
        print("\nTop features:")
        for feature in theme_analysis['features'][:3]:
            print(f"  • {feature['name']} (Score: {feature['relevance']:.3f})")
    
    # Example 2: Similar mechanics
    print("\n2. Finding similar combat mechanics:")
    mechanics = agent.find_similar_game_mechanics("turn-based combat strategy")
    
    print(f"Found combat mechanics in {len(mechanics)} games:")
    for game_id, features in list(mechanics.items())[:3]:
        print(f"  • Game {game_id}: {len(features)} features")
    
    # Example 3: UI patterns
    print("\n3. Analyzing inventory UI patterns:")
    ui_patterns = agent.analyze_ui_patterns("inventory items storage management")
    
    print(f"Found {len(ui_patterns)} UI examples:")
    for pattern in ui_patterns[:3]:
        print(f"  • {pattern['game_id']}: {pattern['ui_description'][:50]}...")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ChromaDB integration examples")
    parser.add_argument("--mode", choices=["cli", "streamlit"], default="cli", 
                       help="Run mode: cli for command line, streamlit for web app")
    
    args = parser.parse_args()
    
    if args.mode == "streamlit":
        print("Run this with: streamlit run ChromaDB/example_integration.py -- --mode streamlit")
        streamlit_example()
    else:
        cli_example()

if __name__ == "__main__":
    main() 