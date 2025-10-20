# CTCC YAML Input Explorer

A beautiful, interactive documentation tool for exploring all input parameters in the Comprehensive Transmission Cost Calculator (CTCC).

## 🚀 Quick Start

1. **Open the documentation**: Simply open `docs/yaml_input_explorer.html` in any modern web browser
2. **No server required**: The documentation is completely self-contained
3. **Interactive features**: Search, filter, explore, and export data

## 📊 What You'll See

### System Overview

- **21 YAML files** containing **4,922 input fields**
- **128 project configurations** covering different transmission line types
- **7 categories** organized by function (Technical, Physical, Financial, etc.)

### Interactive Features

- **🔍 Real-time search** across all field names and descriptions
- **🏷️ Category filtering** to focus on specific areas
- **🌙 Dark/Light mode** toggle with persistent preferences
- **📊 Mermaid diagrams** showing system architecture
- **📥 CSV export** of all field data
- **🔗 Direct linking** to specific fields via URL hash

## 🎨 Visual Design

The documentation features:

- **Modern, responsive design** that works on all devices
- **Color-coded categories** for easy navigation
- **Smooth animations** and hover effects
- **Professional typography** and spacing
- **Accessible design** with proper contrast ratios

## 📁 File Structure

```
docs/
├── yaml_input_explorer.html    # Main interactive documentation
├── yaml_structure.json         # Parsed YAML data (5MB)
└── mermaid_diagram.txt         # Generated Mermaid diagram code
```

## 🔧 Technical Details

### Technologies Used

- **Mermaid.js** for beautiful network diagrams
- **Vanilla JavaScript** for interactivity (no frameworks)
- **CSS Grid/Flexbox** for responsive layout
- **Local Storage** for user preferences

### Data Processing

- **Python script** (`generate_yaml_docs.py`) parses all YAML files
- **Automatic categorization** based on filename patterns
- **Field type detection** and comment extraction
- **Hierarchical structure** preservation

## 🎯 Categories Overview

| Category           | Files | Fields | Description                                  |
| ------------------ | ----- | ------ | -------------------------------------------- |
| **Technical**      | 2     | 70     | Project specifications and technical details |
| **Physical**       | 1     | 18     | Terrain and physical characteristics         |
| **Financial**      | 3     | 14     | Financing, insurance, and delay costs        |
| **Operations**     | 5     | 2,604  | Build costs and O&M operations               |
| **Environmental**  | 4     | 121    | Environmental impacts and mitigation         |
| **Benefits**       | 3     | 25     | Congestion, curtailment, and outage benefits |
| **Configurations** | 3     | 2,070  | 128 project configuration templates          |

## 🚀 Future Enhancements

This documentation is designed to be **future-ready**:

- **Methodology connections** can be added when available
- **Dependency mapping** between fields
- **Interactive cost calculators**
- **Real-time validation** of input values
- **API integration** for live data updates

## 💡 Usage Tips

1. **Start with the overview diagram** to understand the system architecture
2. **Use category filters** to focus on specific areas of interest
3. **Search is powerful** - try searching for units like "MW", "kV", or "miles"
4. **Click on YAML files** to expand and see individual fields
5. **Export to CSV** for offline analysis or integration with other tools
6. **Bookmark specific sections** using the URL hash navigation

## 🎨 Customization

The documentation is easily customizable:

- **Colors**: Modify CSS custom properties in `:root`
- **Layout**: Adjust grid templates and flexbox properties
- **Content**: Update the Python parser to include additional metadata
- **Styling**: All styles are contained in the HTML file for easy modification

---

**Created for the Comprehensive Transmission Cost Calculator (CTCC)**
_Interactive documentation that makes complex data accessible and beautiful._
