#!/usr/bin/env python3
"""
YAML Documentation Generator
Parses all YAML configuration files and generates structured data for interactive documentation.
"""

import os
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class YAMLParser:
    def __init__(self, yamls_dir: str = "yamls"):
        self.yamls_dir = Path(yamls_dir)
        self.data = {
            "metadata": {
                "total_yamls": 0,
                "total_fields": 0,
                "total_configurations": 0,
                "categories": {}
            },
            "yamls": {},
            "field_index": {},
            "categories": {
                "Technical": [],
                "Physical": [],
                "Financial": [],
                "Costs": [],
                "Operations": [],
                "Environmental": [],
                "Benefits": [],
                "Configurations": []
            }
        }
    
    def categorize_yaml(self, filename: str) -> str:
        """Categorize YAML file based on its name and content."""
        filename_lower = filename.lower()
        
        if any(x in filename_lower for x in ["technical", "physical"]):
            return "Technical" if "technical" in filename_lower else "Physical"
        elif any(x in filename_lower for x in ["financing", "insurance", "delays"]):
            return "Financial"
        elif any(x in filename_lower for x in ["build_costs", "om_", "vegetation"]):
            return "Operations"
        elif any(x in filename_lower for x in ["environmental", "emissions", "wildfire"]):
            return "Environmental"
        elif any(x in filename_lower for x in ["congestion", "avoided"]):
            return "Benefits"
        elif any(x in filename_lower for x in ["category", "template", "circuit", "resistance"]):
            return "Configurations"
        else:
            return "Technical"  # Default fallback
    
    def extract_comments(self, content: str) -> Dict[str, str]:
        """Extract comments from YAML content."""
        comments = {}
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                # Look for field comments on the same line or next line
                comment_text = line.strip()[1:].strip()
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith('#'):
                        # Extract field name from next line
                        field_match = re.match(r'^([^:]+):', next_line)
                        if field_match:
                            field_name = field_match.group(1).strip()
                            comments[field_name] = comment_text
        
        return comments
    
    def analyze_value(self, value: Any) -> Dict[str, Any]:
        """Analyze a value to determine its type and characteristics."""
        analysis = {
            "type": type(value).__name__,
            "default": value,
            "units": None,
            "description": None
        }
        
        if isinstance(value, str):
            # Check for units in comments or values
            if any(unit in value.lower() for unit in ['mw', 'kv', 'ohms', 'miles', '%', '$', 'years']):
                analysis["units"] = "detected"
        
        return analysis
    
    def parse_yaml_structure(self, content: Dict[str, Any], path: str = "", comments: Dict[str, str] = None) -> Dict[str, Any]:
        """Recursively parse YAML structure to extract all fields."""
        if comments is None:
            comments = {}
        
        structure = {
            "type": "object",
            "fields": {},
            "subsections": {},
            "field_count": 0
        }
        
        for key, value in content.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # It's a subsection
                structure["subsections"][key] = self.parse_yaml_structure(
                    value, current_path, comments
                )
                structure["field_count"] += structure["subsections"][key]["field_count"]
            else:
                # It's a field
                field_analysis = self.analyze_value(value)
                field_analysis["path"] = current_path
                field_analysis["description"] = comments.get(key, "")
                
                structure["fields"][key] = field_analysis
                structure["field_count"] += 1
                
                # Add to field index
                self.data["field_index"][current_path] = {
                    "yaml_file": path.split('.')[0] if '.' in path else path,
                    "field_name": key,
                    "full_path": current_path,
                    "type": field_analysis["type"],
                    "default": field_analysis["default"],
                    "description": field_analysis["description"]
                }
        
        return structure
    
    def count_project_configurations(self, yaml_data: Dict[str, Any]) -> int:
        """Count the number of project configurations in category YAMLs."""
        count = 0
        
        for filename, data in yaml_data.items():
            if "category" in filename.lower() or "template" in filename.lower():
                # Look for configuration patterns
                content = data.get("content", {})
                for key, value in content.items():
                    if isinstance(value, dict):
                        # Count configurations in nested structures
                        for subkey in value.keys():
                            if isinstance(value[subkey], dict):
                                count += len(value[subkey])
        
        return count
    
    def parse_yaml_file(self, filepath: Path) -> Dict[str, Any]:
        """Parse a single YAML file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            yaml_data = yaml.safe_load(content)
            comments = self.extract_comments(content)
            
            structure = self.parse_yaml_structure(yaml_data, filepath.stem, comments)
            
            return {
                "filename": filepath.name,
                "filepath": str(filepath),
                "category": self.categorize_yaml(filepath.name),
                "structure": structure,
                "field_count": structure["field_count"],
                "comments": comments,
                "raw_content": content
            }
        
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None
    
    def parse_all_yamls(self):
        """Parse all YAML files in the directory."""
        yaml_files = list(self.yamls_dir.glob("*.yaml"))
        
        for yaml_file in sorted(yaml_files):
            parsed_data = self.parse_yaml_file(yaml_file)
            if parsed_data:
                filename = yaml_file.name
                self.data["yamls"][filename] = parsed_data
                
                # Add to category
                category = parsed_data["category"]
                self.data["categories"][category].append(filename)
        
        # Update metadata
        self.data["metadata"]["total_yamls"] = len(self.data["yamls"])
        self.data["metadata"]["total_fields"] = sum(
            yaml_data["field_count"] for yaml_data in self.data["yamls"].values()
        )
        self.data["metadata"]["total_configurations"] = self.count_project_configurations(self.data["yamls"])
        
        # Count fields per category
        for category, files in self.data["categories"].items():
            field_count = sum(
                self.data["yamls"][filename]["field_count"] 
                for filename in files 
                if filename in self.data["yamls"]
            )
            self.data["metadata"]["categories"][category] = {
                "file_count": len(files),
                "field_count": field_count
            }
    
    def generate_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram code for the visualization."""
        # Map category names to node IDs
        category_to_node = {
            "Technical": "Tech",
            "Physical": "Phys",
            "Financial": "Fin",
            "Operations": "Ops",
            "Environmental": "Env",
            "Benefits": "Benefits",
            "Configurations": "Configs"
        }
        
        mermaid = """graph TD
    Root["FORGE Input Parameters<br/>📊 {total_yamls} YAMLs<br/>🔢 {total_fields} Fields<br/>⚙️ {total_configs} Configs"]
    
    Root --> Tech["Technical Details<br/>📋 {tech_count} fields"]
    Root --> Phys["Physical Details<br/>🌍 {phys_count} fields"]
    Root --> Fin["Financial<br/>💰 {fin_count} fields"]
    Root --> Ops["Operations & Costs<br/>🔧 {ops_count} fields"]
    Root --> Env["Environmental<br/>🌱 {env_count} fields"]
    Root --> Benefits["Benefits<br/>📈 {ben_count} fields"]
    Root --> Configs["Configurations<br/>⚙️ {config_count} fields"]
""".format(
            total_yamls=self.data["metadata"]["total_yamls"],
            total_fields=self.data["metadata"]["total_fields"],
            total_configs=self.data["metadata"]["total_configurations"],
            tech_count=self.data["metadata"]["categories"]["Technical"]["field_count"],
            phys_count=self.data["metadata"]["categories"]["Physical"]["field_count"],
            fin_count=self.data["metadata"]["categories"]["Financial"]["field_count"],
            ops_count=self.data["metadata"]["categories"]["Operations"]["field_count"],
            env_count=self.data["metadata"]["categories"]["Environmental"]["field_count"],
            ben_count=self.data["metadata"]["categories"]["Benefits"]["field_count"],
            config_count=self.data["metadata"]["categories"]["Configurations"]["field_count"]
        )
        
        # Add YAML files to each category
        for category, files in self.data["categories"].items():
            if files:
                # Get the node ID for this category
                node_id = category_to_node.get(category, category)
                for filename in files:
                    yaml_data = self.data["yamls"][filename]
                    field_count = yaml_data["field_count"]
                    clean_name = filename.replace('.yaml', '').replace('_', ' ').title()
                    file_node_id = filename.replace(".", "_").replace("-", "_").replace("(", "").replace(")", "").replace(" ", "_")
                    mermaid += f'\n    {node_id} --> {file_node_id}["{clean_name}<br/>📄 {field_count} fields"]'
        
        return mermaid
    
    def save_data(self, output_file: str = "docs/yaml_structure.json"):
        """Save the parsed data to JSON file."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {output_file}")
        print(f"Total YAMLs: {self.data['metadata']['total_yamls']}")
        print(f"Total Fields: {self.data['metadata']['total_fields']}")
        print(f"Total Configurations: {self.data['metadata']['total_configurations']}")
        
        # Print category breakdown
        print("\nCategory Breakdown:")
        for category, info in self.data["metadata"]["categories"].items():
            print(f"  {category}: {info['file_count']} files, {info['field_count']} fields")

def main():
    """Main function to run the YAML parser."""
    parser = YAMLParser()
    parser.parse_all_yamls()
    parser.save_data()
    
    # Generate and save Mermaid diagram
    mermaid_code = parser.generate_mermaid_diagram()
    with open("docs/mermaid_diagram.txt", "w") as f:
        f.write(mermaid_code)
    
    print(f"\nMermaid diagram saved to docs/mermaid_diagram.txt")

if __name__ == "__main__":
    main()
