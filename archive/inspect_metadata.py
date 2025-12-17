# Method 1: Quick inspection script
# Save this as inspect_metadata.py and run it

import pickle
import json
from pathlib import Path

def inspect_metadata():
    """Inspect the metadata.pkl file to understand its structure"""
    
    # Path to your metadata file
    metadata_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/vectorstore/metadata.pkl"
    
    print("🔍 Inspecting metadata.pkl file...")
    print("="*60)
    
    try:
        # Check if file exists
        if not Path(metadata_path).exists():
            print("❌ metadata.pkl file not found!")
            print(f"Expected location: {metadata_path}")
            return
        
        # Load the pickle file
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)
        
        print("✅ Successfully loaded metadata.pkl")
        print(f"📊 Data type: {type(metadata)}")
        print(f"📏 Size: {len(metadata) if hasattr(metadata, '__len__') else 'N/A'}")
        print("\n" + "="*60)
        
        # Inspect the contents
        if isinstance(metadata, dict):
            print("📝 DICTIONARY CONTENTS:")
            print("-" * 30)
            
            for key, value in metadata.items():
                print(f"🔑 Key: '{key}'")
                print(f"   Type: {type(value)}")
                
                if isinstance(value, (list, tuple)):
                    print(f"   Length: {len(value)}")
                    if len(value) > 0:
                        print(f"   First item: {value[0]}")
                        if len(value) > 5:
                            print(f"   Sample items: {value[:3]}...")
                        else:
                            print(f"   All items: {value}")
                elif isinstance(value, (int, float, str)):
                    print(f"   Value: {value}")
                elif isinstance(value, dict):
                    print(f"   Dict keys: {list(value.keys())}")
                else:
                    print(f"   Value: {str(value)[:100]}...")
                
                print()
        
        elif isinstance(metadata, list):
            print("📝 LIST CONTENTS:")
            print("-" * 30)
            print(f"   Length: {len(metadata)}")
            if len(metadata) > 0:
                print(f"   First item type: {type(metadata[0])}")
                print(f"   First item: {metadata[0]}")
        
        else:
            print("📝 OTHER DATA TYPE:")
            print("-" * 30)
            print(f"   Content: {metadata}")
        
        print("\n" + "="*60)
        print("💡 RECOMMENDATIONS FOR FLASK APP:")
        print("-" * 30)
        
        if isinstance(metadata, dict):
            # Suggest which keys to use for stats
            possible_faq_keys = [k for k in metadata.keys() if any(word in k.lower() for word in ['total', 'count', 'qa', 'faq', 'question'])]
            possible_category_keys = [k for k in metadata.keys() if any(word in k.lower() for word in ['categor', 'topic', 'type'])]
            
            if possible_faq_keys:
                print(f"🔢 Possible FAQ count keys: {possible_faq_keys}")
            if possible_category_keys:
                print(f"📂 Possible category keys: {possible_category_keys}")
            
            print(f"\n📋 Update your Flask /api/stats route to use:")
            print(f"   total_faqs = metadata.get('{possible_faq_keys[0] if possible_faq_keys else 'your_key_here'}', 0)")
            if possible_category_keys:
                categories_key = possible_category_keys[0]
                print(f"   categories = metadata.get('{categories_key}', [])")
                print(f"   total_categories = len(categories)")
        
    except Exception as e:
        print(f"❌ Error loading metadata: {e}")
        print("\n💡 This might mean:")
        print("   - The file is corrupted")
        print("   - It was created with a different Python version")
        print("   - It's not actually a pickle file")

if __name__ == "__main__":
    inspect_metadata()


