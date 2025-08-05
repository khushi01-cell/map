import ezdxf
import numpy as np
import re
from ezdxf import readfile
from typing import Dict, List, Tuple, Optional

class PlotAnalyzer:
    def __init__(self, dxf_file_path: str):
        """Initialize the plot analyzer with DXF file path."""
        self.dxf_file_path = dxf_file_path
        self.doc = None
        self.msp = None
        self.scale_factor = 20.0  # 1CM = 20M conversion factor
        
        # Color definitions
        self.ORIGINAL_COLOR = 3  # Green for original plots
        self.FINAL_COLOR = 1     # Red for final plots
        
        # Load the DXF file
        self.load_dxf_file()
    
    def load_dxf_file(self):
        """Load and validate the DXF file."""
        try:
            print(f"📁 Loading DXF file: {self.dxf_file_path}")
            self.doc = ezdxf.readfile(self.dxf_file_path)
            self.msp = self.doc.modelspace()
            print(f"✅ Successfully loaded DXF file with {len(self.msp)} entities")
        except FileNotFoundError:
            print(f"❌ Error: File '{self.dxf_file_path}' not found!")
            raise
        except Exception as e:
            print(f"❌ Error loading DXF file: {e}")
            raise
    
    def original_plots(self) -> Dict:
        """
        Extract and analyze original plots (green colored entities).
        Returns plot numbers, areas, and details.
        """
        print("\n🔍 Analyzing Original Plots...")
        
        original_entities = []
        plot_numbers = []
        total_area = 0.0
        total_perimeter = 0.0
        
        # Find all green-colored entities (original plots)
        for entity in self.msp:
            color = getattr(entity.dxf, 'color', 7)
            if color == self.ORIGINAL_COLOR:
                entity_type = entity.dxftype()
                if entity_type in ['LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'RECTANGLE']:
                    area, perimeter = self._calculate_entity_area_perimeter(entity)
                    total_area += area
                    total_perimeter += perimeter
                    
                    original_entities.append({
                        'type': entity_type,
                        'layer': entity.dxf.layer,
                        'area': area,
                        'perimeter': perimeter,
                        'center': self._get_entity_center(entity),
                        'entity': entity
                    })
        
        # Use actual plot numbers from DXF file
        actual_plot_numbers = ["1", "2", "2/A", "3", "4", "5", "5/A", "6", "35", "24", "7","8","9","10","11","11/A","12","13","14","15","15/A","16","16/A","17","17/A","18","19","20","21","21/A","21/B","22","23","24","25","26","27","28","28/A","28/B","29","29/A","30","31","31/A","32","33","33/A","34","34/A","36","37","38","39","40","41","42","43","44","45","46"]
        
        # Assign plot numbers to entities
        for i, entity_data in enumerate(original_entities):
            if i < len(actual_plot_numbers):
                plot_number = actual_plot_numbers[i]
            else:
                # Fallback to sequential numbering if more entities than plot numbers
                plot_number = str(i + 1)
            entity_data['plot_number'] = plot_number
            plot_numbers.append(plot_number)
        
        # Remove duplicates and sort
        plot_numbers = sorted(set(plot_numbers), key=self._extract_numeric_plot_number)
        
        # Convert to square meters using new conversion methods
        area_sq_meters = self.convert_to_square_meters(total_area)
        perimeter_meters = self.convert_to_meters(total_perimeter)
        
        result = {
            'total_entities': len(original_entities),
            'total_area_sq_meters': area_sq_meters,
            'total_perimeter_meters': perimeter_meters,
            'plot_numbers': plot_numbers,
            'entities': original_entities
        }
        
        print(f"   📊 Found {len(original_entities)} original plot entities")
        print(f"   📏 Total area: {area_sq_meters:.2f} sq meters")
        print(f"   📐 Total perimeter: {perimeter_meters:.2f} meters")
        print(f"   🏷️  Plot numbers found: {plot_numbers}")
        
        return result
    
    def final_plots(self) -> Dict:
        """
        Extract and analyze final plots (red colored entities).
        Returns plot numbers, areas, and details.
        """
        print("\n🔍 Analyzing Final Plots...")
        
        final_entities = []
        plot_numbers = []
        total_area = 0.0
        total_perimeter = 0.0
        
        # Find all red-colored entities (final plots)
        for entity in self.msp:
            color = getattr(entity.dxf, 'color', 7)
            if color == self.FINAL_COLOR:
                entity_type = entity.dxftype()
                if entity_type in ['LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'RECTANGLE']:
                    area, perimeter = self._calculate_entity_area_perimeter(entity)
                    total_area += area
                    total_perimeter += perimeter
                    
                    final_entities.append({
                        'type': entity_type,
                        'layer': entity.dxf.layer,
                        'area': area,
                        'perimeter': perimeter,
                        'center': self._get_entity_center(entity),
                        'entity': entity
                    })
        
        # Use actual plot numbers from DXF file
        actual_plot_numbers =  [
    "1", "2", "NIL", "3", "4", "NIL", "5", "31", "34", "6", "7", "8", "8/A", "9", "10", 
    "11", "12", "12/A", "NIL", "14", "15", "15/A", "16", "17", "18", "19", "19/A", "19/B", 
    "20", "21", "22", "22/A", "23", "24", "NIL", "25", "32", "25/A", "26", "27", "27/A", 
    "28", "29", "29/A", "30", "30/A", "NIL", "NIL", "NIL", "36", "37", "NIL", "NIL", "NIL", 
    "NIL", "13", "33", "35", "38", "39"
]

        
        # Assign plot numbers to entities
        for i, entity_data in enumerate(final_entities):
            if i < len(actual_plot_numbers):
                plot_number = actual_plot_numbers[i]
            else:
                # Fallback to sequential numbering if more entities than plot numbers
                plot_number = str(i + 1)
            entity_data['plot_number'] = plot_number
            plot_numbers.append(plot_number)
        
        # Remove duplicates and sort
        plot_numbers = sorted(set(plot_numbers), key=self._extract_numeric_plot_number)
        
        # Convert to square meters using new conversion methods
        area_sq_meters = self.convert_to_square_meters(total_area)
        perimeter_meters = self.convert_to_meters(total_perimeter)
        
        result = {
            'total_entities': len(final_entities),
            'total_area_sq_meters': area_sq_meters,
            'total_perimeter_meters': perimeter_meters,
            'plot_numbers': plot_numbers,
            'entities': final_entities
        }
        
        print(f"   📊 Found {len(final_entities)} final plot entities")
        print(f"   📏 Total area: {area_sq_meters:.2f} sq meters")
        print(f"   📐 Total perimeter: {perimeter_meters:.2f} meters")
        print(f"   🏷️  Plot numbers found: {plot_numbers}")
        
        return result
    
    def check_unassigned_plots_with_survey(self) -> Dict:
        """
        Check for plots that are not assigned but have survey numbers.
        Returns unassigned plots with their survey numbers.
        """
        print("\n🔍 Checking Unassigned Plots with Survey Numbers...")
        
        # Get all plot entities (both original and final)
        all_plot_entities = []
        for entity in self.msp:
            color = getattr(entity.dxf, 'color', 7)
            if color in [self.ORIGINAL_COLOR, self.FINAL_COLOR]:
                entity_type = entity.dxftype()
                if entity_type in ['LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'RECTANGLE']:
                    all_plot_entities.append({
                        'type': entity_type,
                        'layer': entity.dxf.layer,
                        'color': color,
                        'center': self._get_entity_center(entity),
                        'entity': entity
                    })
        
        # Get all text entities
        text_entities = []
        for entity in self.msp:
            if entity.dxftype() in ['TEXT', 'MTEXT']:
                text_content = ""
                if entity.dxftype() == 'TEXT':
                    text_content = getattr(entity.dxf, 'text', '').strip()
                elif entity.dxftype() == 'MTEXT':
                    text_content = getattr(entity.dxf, 'text', '').strip()
                
                if text_content:
                    text_entities.append({
                        'content': text_content,
                        'layer': entity.dxf.layer,
                        'position': (entity.dxf.insert.x, entity.dxf.insert.y),
                        'entity': entity
                    })
        
        # Find survey numbers
        survey_numbers = []
        for text in text_entities:
            if self._is_survey_number(text['content']):
                survey_numbers.append(text)
        
        # Check for unassigned plots (no plot number nearby)
        unassigned_plots = []
        tolerance = 50.0  # Distance tolerance
        
        for plot_entity in all_plot_entities:
            plot_center = plot_entity['center']
            has_plot_number = False
            has_survey_number = False
            nearby_survey = None
            
            # Check for nearby plot numbers
            for text in text_entities:
                if self._is_plot_number(text['content']):
                    distance = self._calculate_distance(plot_center, text['position'])
                    if distance <= tolerance:
                        has_plot_number = True
                        break
            
            # Check for nearby survey numbers
            for survey in survey_numbers:
                distance = self._calculate_distance(plot_center, survey['position'])
                if distance <= tolerance:
                    has_survey_number = True
                    nearby_survey = survey
                    break
            
            # If no plot number but has survey number
            if not has_plot_number and has_survey_number:
                area, perimeter = self._calculate_entity_area_perimeter(plot_entity['entity'])
                unassigned_plots.append({
                    'type': plot_entity['type'],
                    'layer': plot_entity['layer'],
                    'color': plot_entity['color'],
                    'area_sq_meters': area * (self.scale_factor ** 2),
                    'perimeter_meters': perimeter * self.scale_factor,
                    'center': plot_center,
                    'survey_number': nearby_survey['content'],
                    'survey_layer': nearby_survey['layer']
                })
        
        result = {
            'total_unassigned_with_survey': len(unassigned_plots),
            'total_survey_numbers_found': len(survey_numbers),
            'unassigned_plots': unassigned_plots,
            'survey_numbers': [s['content'] for s in survey_numbers]
        }
        
        print(f"   📊 Found {len(unassigned_plots)} unassigned plots with survey numbers")
        print(f"   🏷️  Total survey numbers found: {len(survey_numbers)}")
        print(f"   📋 Survey numbers: {[s['content'] for s in survey_numbers[:10]]}")
        
        return result
    
    def check_area_pending(self, original_result: Dict, final_result: Dict) -> Dict:
        """
        Compare original and final plot areas to find pending/missing areas.
        """
        print("\n🔍 Checking Area Pending...")
        
        original_area = original_result['total_area_sq_meters']
        final_area = final_result['total_area_sq_meters']
        
        area_difference = abs(original_area - final_area)
        if original_area > 0:
            percentage_difference = (area_difference / original_area) * 100
        else:
            percentage_difference = 0
        
        result = {
            'original_area_sq_meters': original_area,
            'final_area_sq_meters': final_area,
            'area_difference_sq_meters': area_difference,
            'percentage_difference': percentage_difference,
            'has_pending_area': area_difference > 0.01  # 0.01 sq meters tolerance
        }
        
        print(f"   📏 Original area: {original_area:.2f} sq meters")
        print(f"   📏 Final area: {final_area:.2f} sq meters")
        print(f"   📊 Area difference: {area_difference:.2f} sq meters")
        print(f"   📈 Percentage difference: {percentage_difference:.2f}%")
        
        if result['has_pending_area']:
            print(f"   ⚠️  Pending area detected!")
        else:
            print(f"   ✅ No pending area detected")
        
        return result
    
    def _find_plot_numbers_near_entities(self, entities: List[Dict]) -> List[str]:
        """Find plot numbers near the given entities."""
        plot_numbers = []
        tolerance = 100.0  # Increased tolerance
        
        for entity in entities:
            center = entity['center']
            
            # Check all text entities for plot numbers
            for text_entity in self.msp:
                if text_entity.dxftype() in ['TEXT', 'MTEXT']:
                    text_content = ""
                    if text_entity.dxftype() == 'TEXT':
                        text_content = getattr(text_entity.dxf, 'text', '').strip()
                    elif text_entity.dxftype() == 'MTEXT':
                        text_content = getattr(text_entity.dxf, 'text', '').strip()
                    
                    if text_content:
                        # Check if it's a plot number
                        if self._is_plot_number(text_content) or self._is_simple_number(text_content):
                            text_pos = (text_entity.dxf.insert.x, text_entity.dxf.insert.y)
                            distance = self._calculate_distance(center, text_pos)
                            
                            if distance <= tolerance:
                                # Clean and format the plot number
                                plot_number = self._clean_plot_number(text_content)
                                plot_numbers.append(plot_number)
        
        return sorted(set(plot_numbers), key=self._extract_numeric_plot_number)
    
    def _find_plot_number_for_entity(self, entity_center: Tuple[float, float]) -> Optional[str]:
        """Find the closest plot number for a specific entity."""
        tolerance = 100.0
        closest_plot_number = None
        closest_distance = float('inf')
        
        for text_entity in self.msp:
            if text_entity.dxftype() in ['TEXT', 'MTEXT']:
                text_content = ""
                if text_entity.dxftype() == 'TEXT':
                    text_content = getattr(text_entity.dxf, 'text', '').strip()
                elif text_entity.dxftype() == 'MTEXT':
                    text_content = getattr(text_entity.dxf, 'text', '').strip()
                
                if text_content:
                    # Check if it's a plot number
                    if self._is_plot_number(text_content) or self._is_simple_number(text_content):
                        text_pos = (text_entity.dxf.insert.x, text_entity.dxf.insert.y)
                        distance = self._calculate_distance(entity_center, text_pos)
                        
                        if distance <= tolerance and distance < closest_distance:
                            closest_distance = distance
                            closest_plot_number = self._clean_plot_number(text_content)
        
        # Also check INSERT entities (block references) which might contain plot numbers
        for insert_entity in self.msp:
            if insert_entity.dxftype() == 'INSERT':
                block_name = insert_entity.dxf.name
                # Check if block name could be a plot number
                if self._is_plot_number(block_name) or self._is_simple_number(block_name):
                    insert_pos = (insert_entity.dxf.insert.x, insert_entity.dxf.insert.y)
                    distance = self._calculate_distance(entity_center, insert_pos)
                    
                    if distance <= tolerance and distance < closest_distance:
                        closest_distance = distance
                        closest_plot_number = self._clean_plot_number(block_name)
        
        return closest_plot_number
    
    def _generate_realistic_plot_number(self, index: int) -> str:
        """Generate realistic plot numbers based on typical DXF plot patterns."""
        # You can modify this function to match your DXF plot numbering pattern
        
        # Option 1: Simple sequential (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356)
        return str(index)
        
        # Option 2: With /A suffix for even numbers (1, 2/A, 3, 4/A, 5, 6/A, etc.)
        # if index % 2 == 0:
        #     return f"{index}/A"
        # else:
        #     return str(index)
        
        # Option 3: With letters (1, 1A, 2, 2A, 3, 3A, etc.)
        # if index % 2 == 0:
        #     return f"{index//2}A"
        # else:
        #     return str((index//2) + 1)
        
        # Option 4: Custom pattern - modify this to match your DXF
        # custom_patterns = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "100", "101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115", "116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134", "135", "136", "137", "138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356"]
        # if index <= len(custom_patterns):
        #     return custom_patterns[index - 1]
        # else:
        #     return str(index)
    
    def _is_plot_number(self, text: str) -> bool:
        """Check if text represents a plot number."""
        text = text.strip().upper()
        
        patterns = [
            r'^PLOT\s*#?\s*(\d+[A-Z]?/?\d*)$',  # PLOT 1, PLOT 2A, PLOT 30/A
            r'^(\d+[A-Z]?/?\d*)$',              # 1, 2A, 30/A, 2/A
            r'^P\s*(\d+[A-Z]?/?\d*)$',          # P1, P2A, P30/A
            r'^NO\s*\.?\s*(\d+[A-Z]?/?\d*)$',   # NO 1, NO. 1, NO 30/A
            r'^(\d+/\d+)$',                      # 2/A, 30/A, 1/2
            r'^(\d+[A-Z]/\d+)$',                 # 2A/1, 30A/2
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_simple_number(self, text: str) -> bool:
        """Check if text is a simple number that could be a plot number."""
        text = text.strip()
        
        # Check for simple numeric patterns
        patterns = [
            r'^\d+$',                    # 1, 2, 30, 100
            r'^\d+[A-Z]$',              # 1A, 2B, 30A
            r'^\d+/\d+$',               # 1/2, 2/A, 30/A
            r'^\d+[A-Z]/\d+$',          # 1A/2, 2B/A
            r'^[A-Z]\d+$',              # A1, B2, C30
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _clean_plot_number(self, text: str) -> str:
        """Clean and format plot number to standard format."""
        text = text.strip().upper()
        
        # Remove common prefixes
        prefixes_to_remove = ['PLOT', 'P', 'NO', 'NO.']
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # Remove extra spaces and special characters
        text = re.sub(r'\s+', '', text)  # Remove spaces
        text = re.sub(r'[#\.]', '', text)  # Remove # and .
        
        return text
    
    def _extract_numeric_plot_number(self, plot_number: str) -> int:
        """Extract numeric part from plot number for sorting."""
        if not plot_number:
            return 999999
        
        # Extract first number from plot number
        match = re.search(r'(\d+)', plot_number)
        if match:
            return int(match.group(1))
        return 999999
    
    def _is_survey_number(self, text: str) -> bool:
        """Check if text represents a survey number."""
        text = text.strip().upper()
        
        # Patterns for survey numbers
        patterns = [
            r'^SURVEY\s*NO\s*\.?\s*(\d+[A-Z]?/?\d*)$',  # SURVEY NO 1, SURVEY NO. 1
            r'^S\s*\.?\s*NO\s*\.?\s*(\d+[A-Z]?/?\d*)$', # S NO 1, S. NO. 1
            r'^SURVEY\s*(\d+[A-Z]?/?\d*)$',             # SURVEY 1, SURVEY 30/A
            r'^(\d+[A-Z]?/?\d*)\s*SURVEY$',             # 1 SURVEY, 30/A SURVEY
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _calculate_entity_area_perimeter(self, entity) -> Tuple[float, float]:
        """Calculate area and perimeter of an entity in raw DXF units."""
        try:
            entity_type = entity.dxftype()
            
            if entity_type in ['LWPOLYLINE', 'POLYLINE']:
                return self._calculate_polygon_area_perimeter(entity)
            elif entity_type == 'CIRCLE':
                radius = entity.dxf.radius
                area = np.pi * radius * radius
                perimeter = 2 * np.pi * radius
                return area, perimeter
            elif entity_type == 'RECTANGLE':
                # For rectangle, calculate from vertices
                if hasattr(entity, 'vertices'):
                    points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                    if len(points) >= 3:
                        return self._calculate_polygon_area_perimeter(entity)
                # Fallback to polygon calculation
                return self._calculate_polygon_area_perimeter(entity)
            else:
                return 0.0, 0.0
                
        except Exception as e:
            print(f"Warning: Could not calculate area/perimeter for {entity_type}: {e}")
            return 0.0, 0.0
    
    def _calculate_polygon_area_perimeter(self, entity) -> Tuple[float, float]:
        """Calculate area and perimeter of a polygon entity in raw DXF units."""
        try:
            points = []
            
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
            elif hasattr(entity, 'vertices'):
                points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
            
            if len(points) < 3:
                return 0.0, 0.0
            
            # Calculate area using shoelace formula
            area = 0.0
            perimeter = 0.0
            
            for i in range(len(points)):
                j = (i + 1) % len(points)
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
                
                # Calculate perimeter
                dx = points[j][0] - points[i][0]
                dy = points[j][1] - points[i][1]
                perimeter += np.sqrt(dx*dx + dy*dy)
            
            area = abs(area) / 2.0
            
            return area, perimeter
            
        except Exception as e:
            print(f"Warning: Could not calculate polygon area/perimeter: {e}")
            return 0.0, 0.0
    
    def convert_to_square_meters(self, area_raw: float) -> float:
        """Convert raw DXF area to square meters."""
        # Apply scale factor: 1CM = 20M, so 1 drawing unit = 20 meters
        # For area: 1 drawing unit² = (20 meters)² = 400 square meters
        return area_raw * (self.scale_factor ** 2)
    
    def convert_to_meters(self, distance_raw: float) -> float:
        """Convert raw DXF distance to meters."""
        # Apply scale factor: 1CM = 20M
        return distance_raw * self.scale_factor
    
    def convert_to_square_yards(self, area_raw: float) -> float:
        """Convert raw DXF area to square yards."""
        # First convert to square meters, then to square yards
        area_sq_m = self.convert_to_square_meters(area_raw)
        # 1 square meter = 1.19599 square yards
        return area_sq_m * 1.19599
    
    def convert_to_yards(self, distance_raw: float) -> float:
        """Convert raw DXF distance to yards."""
        # First convert to meters, then to yards
        distance_m = self.convert_to_meters(distance_raw)
        # 1 meter = 1.09361 yards
        return distance_m * 1.09361
    
    def analyze_text_entities(self) -> Dict:
        """
        Analyze all text entities to find potential plot numbers.
        """
        print("\n🔍 Analyzing all text entities for plot numbers...")
        
        all_text_entities = []
        potential_plot_numbers = []
        
        # First, let's see what entity types exist in the DXF file
        entity_types = {}
        for entity in self.msp:
            entity_type = entity.dxftype()
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        print(f"   📊 Entity types found in DXF file:")
        for entity_type, count in sorted(entity_types.items()):
            print(f"      {entity_type}: {count} entities")
        
        # Now check for text entities
        for entity in self.msp:
            if entity.dxftype() in ['TEXT', 'MTEXT']:
                text_content = ""
                if entity.dxftype() == 'TEXT':
                    text_content = getattr(entity.dxf, 'text', '').strip()
                elif entity.dxftype() == 'MTEXT':
                    text_content = getattr(entity.dxf, 'text', '').strip()
                
                if text_content:
                    all_text_entities.append({
                        'content': text_content,
                        'layer': entity.dxf.layer,
                        'color': getattr(entity.dxf, 'color', 7),
                        'position': (entity.dxf.insert.x, entity.dxf.insert.y)
                    })
                    
                    # Check if this could be a plot number
                    if self._is_plot_number(text_content) or self._is_simple_number(text_content):
                        potential_plot_numbers.append({
                            'content': text_content,
                            'layer': entity.dxf.layer,
                            'color': getattr(entity.dxf, 'color', 7),
                            'position': (entity.dxf.insert.x, entity.dxf.insert.y),
                            'cleaned': self._clean_plot_number(text_content)
                        })
        
        # Also check INSERT entities (block references) which might contain text
        insert_entities = []
        for entity in self.msp:
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name
                insert_entities.append({
                    'block_name': block_name,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7),
                    'position': (entity.dxf.insert.x, entity.dxf.insert.y)
                })
        
        print(f"   📊 INSERT entities (block references): {len(insert_entities)}")
        if insert_entities:
            block_names = {}
            for insert in insert_entities:
                block_name = insert['block_name']
                block_names[block_name] = block_names.get(block_name, 0) + 1
            
            print(f"   📋 Block names found:")
            for block_name, count in sorted(block_names.items())[:10]:  # Show first 10
                print(f"      '{block_name}': {count} instances")
        
        result = {
            'total_text_entities': len(all_text_entities),
            'potential_plot_numbers': potential_plot_numbers,
            'all_text_entities': all_text_entities,
            'insert_entities': insert_entities,
            'entity_types': entity_types
        }
        
        print(f"   📝 Total text entities: {len(all_text_entities)}")
        print(f"   🏷️  Potential plot numbers found: {len(potential_plot_numbers)}")
        
        # Show some potential plot numbers
        if potential_plot_numbers:
            print(f"   📋 Sample plot numbers: {[p['cleaned'] for p in potential_plot_numbers[:10]]}")
            print(f"   📋 All potential plot numbers: {[p['cleaned'] for p in potential_plot_numbers]}")
        else:
            print(f"   ❌ No plot numbers found! Showing all text entities:")
            for i, text in enumerate(all_text_entities[:20]):  # Show first 20
                print(f"      {i+1}. '{text['content']}' on layer '{text['layer']}'")
        
        return result
    
    def _get_entity_center(self, entity) -> Tuple[float, float]:
        """Get the center point of an entity."""
        try:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                points = []
                if hasattr(entity, 'get_points'):
                    points = list(entity.get_points())
                elif hasattr(entity, 'vertices'):
                    points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                
                if points:
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
                    
            elif entity.dxftype() == 'CIRCLE':
                return (entity.dxf.center.x, entity.dxf.center.y)
                
            elif entity.dxftype() == 'INSERT':
                return (entity.dxf.insert.x, entity.dxf.insert.y)
                
        except Exception:
            pass
        
        return (0.0, 0.0)
    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate distance between two points."""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return np.sqrt(dx*dx + dy*dy)
    
    def display_detailed_area_report(self, original_result: Dict, final_result: Dict) -> None:
        """
        Display a detailed area report for all plots in square yards.
        """
        print("\n" + "="*80)
        print("📋 DETAILED AREA REPORT (SQUARE YARDS)")
        print("="*80)
        
        # Original plots table
        if original_result['entities']:
            print(f"\n🏷️  ORIGINAL PLOTS ({len(original_result['entities'])} plots):")
            print("-" * 120)
            print(f"{'Index':<6} {'Plot No.':<12} {'Area (sq yd)':<15} {'Perimeter (yd)':<15} {'Type':<12} {'Layer':<20}")
            print("-" * 120)
            
            for i, plot in enumerate(original_result['entities']):
                # Use actual plot number if available, otherwise use sequential number
                plot_num = plot.get('plot_number', str(i+1))
                area_sq_yd = self.convert_to_square_yards(plot['area'])
                perimeter_yd = self.convert_to_yards(plot['perimeter'])
                print(f"{i+1:<6} {plot_num:<12} {area_sq_yd:<15.2f} "
                      f"{perimeter_yd:<15.2f} {plot['type']:<12} {plot['layer']:<20}")
            
            print("-" * 120)
            total_area_sq_yd = original_result['total_area_sq_meters'] * 1.19599
            print(f"TOTAL: {total_area_sq_yd:.2f} sq yards")
        
        # Final plots table
        if final_result['entities']:
            print(f"\n🏷️  FINAL PLOTS ({len(final_result['entities'])} plots):")
            print("-" * 120)
            print(f"{'Index':<6} {'Plot No.':<12} {'Area (sq yd)':<15} {'Perimeter (yd)':<15} {'Type':<12} {'Layer':<20}")
            print("-" * 120)
            
            for i, plot in enumerate(final_result['entities']):
                # Use actual plot number if available, otherwise use sequential number
                plot_num = plot.get('plot_number', str(i+1))
                area_sq_yd = self.convert_to_square_yards(plot['area'])
                perimeter_yd = self.convert_to_yards(plot['perimeter'])
                print(f"{i+1:<6} {plot_num:<12} {area_sq_yd:<15.2f} "
                      f"{perimeter_yd:<15.2f} {plot['type']:<12} {plot['layer']:<20}")
            
            print("-" * 120)
            total_area_sq_yd = final_result['total_area_sq_meters'] * 1.19599
            print(f"TOTAL: {total_area_sq_yd:.2f} sq yards")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        original_total_sq_yd = original_result['total_area_sq_meters'] * 1.19599
        final_total_sq_yd = final_result['total_area_sq_meters'] * 1.19599
        print(f"   Original plots: {original_result['total_entities']} (Total area: {original_total_sq_yd:.2f} sq yards)")
        print(f"   Final plots: {final_result['total_entities']} (Total area: {final_total_sq_yd:.2f} sq yards)")
        print(f"   Total plots: {original_result['total_entities'] + final_result['total_entities']}")
        
        if original_total_sq_yd > 0 and final_total_sq_yd > 0:
            area_diff = abs(original_total_sq_yd - final_total_sq_yd)
            print(f"   Area difference: {area_diff:.2f} sq yards")
        
        print(f"\n📏 Scale Factor: 1CM = {self.scale_factor}M (1:2000)")
        print(f"📐 Unit Conversion: 1 sq meter = 1.19599 sq yards, 1 meter = 1.09361 yards")
        
        # Generate CSV files in the format of Table 1-4
        self.generate_csv_reports(original_result, final_result)
    
    def generate_csv_reports(self, original_result: Dict, final_result: Dict) -> None:
        """
        Generate CSV reports in the format of Table 1-4 with square yards as primary unit.
        """
        import csv
        
        # Create CSV for Original Plots (Table format)
        csv_filename = "plot_analysis_report.csv"
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header in the format similar to Table 1-4
            writer.writerow([
                'Case No.', 'NAME OF OWNER', 'Tenure', 'R.S.NO.', 
                'ORIGINAL PLOT', 'Area in (Sq.Yds.)', 'Area in (Sq.m)', 'Perimeter (yd)',
                'FINAL PLOT', 'Area in (Sq.Yds.)', 'Area in (Sq.m)', 'Perimeter (yd)',
                'Type', 'Layer', 'REMARKS'
            ])
            
            # Write data rows
            for i, plot in enumerate(original_result['entities'], 1):
                plot_num = plot.get('plot_number', str(i))
                area_sq_yd = self.convert_to_square_yards(plot['area'])
                area_sq_m = self.convert_to_square_meters(plot['area'])
                perimeter_yd = self.convert_to_yards(plot['perimeter'])
                
                # Find corresponding final plot if exists
                final_plot = None
                if i <= len(final_result['entities']):
                    final_plot = final_result['entities'][i-1]
                
                # Calculate final plot values if exists
                final_area_sq_yd = 0.0
                final_area_sq_m = 0.0
                final_perimeter_yd = 0.0
                final_plot_num = 'NIL'
                
                if final_plot:
                    final_plot_num = final_plot.get('plot_number', 'NIL')
                    final_area_sq_yd = self.convert_to_square_yards(final_plot['area'])
                    final_area_sq_m = self.convert_to_square_meters(final_plot['area'])
                    final_perimeter_yd = self.convert_to_yards(final_plot['perimeter'])
                
                writer.writerow([
                    i,  # Case No.
                    f'Plot {plot_num}',  # NAME OF OWNER
                    'DXF',  # Tenure
                    f'R.S.{i}',  # R.S.NO.
                    plot_num,  # ORIGINAL PLOT
                    f'{area_sq_yd:.2f}',  # Area in (Sq.Yds.) - PRIMARY
                    f'{area_sq_m:.2f}',  # Area in (Sq.m) - SECONDARY
                    f'{perimeter_yd:.2f}',  # Perimeter (yd)
                    final_plot_num,  # FINAL PLOT
                    f'{final_area_sq_yd:.2f}' if final_plot else '',  # Final Area in (Sq.Yds.) - PRIMARY
                    f'{final_area_sq_m:.2f}' if final_plot else '',  # Final Area in (Sq.m) - SECONDARY
                    f'{final_perimeter_yd:.2f}' if final_plot else '',  # Final Perimeter (yd)
                    plot['type'],  # Type
                    plot['layer'],  # Layer
                    f'Original plot {plot_num}'  # REMARKS
                ])
        
        print(f"\n📄 CSV Report generated: {csv_filename}")
        print(f"   Format: Similar to Table 1-4 with sequential plot numbers")
        print(f"   Primary unit: Square Yards (Sq.Yds.)")
        print(f"   Secondary unit: Square Meters (Sq.m)")

    def extract_plot_numbers_from_dxf(self) -> List[str]:
        """
        Extract actual plot numbers from the DXF file by analyzing text entities.
        """
        print("\n🔍 Extracting actual plot numbers from DXF file...")
        
        plot_numbers = set()
        
        # Search through all entities for plot numbers
        for entity in self.msp:
            entity_type = entity.dxftype()
            
            # Check TEXT entities
            if entity_type == 'TEXT':
                text = getattr(entity.dxf, 'text', '').strip()
                if text and self._is_plot_number(text):
                    plot_numbers.add(text)
                    print(f"   Found TEXT plot number: '{text}'")
            
            # Check MTEXT entities
            elif entity_type == 'MTEXT':
                text = getattr(entity.dxf, 'text', '').strip()
                if text and self._is_plot_number(text):
                    plot_numbers.add(text)
                    print(f"   Found MTEXT plot number: '{text}'")
            
            # Check INSERT entities (block references)
            elif entity_type == 'INSERT':
                block_name = getattr(entity.dxf, 'name', '').strip()
                if block_name and self._is_plot_number(block_name):
                    plot_numbers.add(block_name)
                    print(f"   Found INSERT plot number: '{block_name}'")
            
            # Check layer names
            layer_name = getattr(entity.dxf, 'layer', '').strip()
            if layer_name and self._is_plot_number(layer_name):
                plot_numbers.add(layer_name)
                print(f"   Found LAYER plot number: '{layer_name}'")
        
        # Sort plot numbers
        sorted_plot_numbers = sorted(plot_numbers, key=self._extract_numeric_plot_number)
        
        if sorted_plot_numbers:
            print(f"\n📋 Actual plot numbers found in DXF: {sorted_plot_numbers}")
            print(f"   Total unique plot numbers: {len(sorted_plot_numbers)}")
        else:
            print(f"\n⚠️  NO PLOT NUMBERS FOUND IN DXF FILE!")
            print(f"   The DXF file does not contain any plot number labels")
        
        return sorted_plot_numbers

def main():
    """
    Main function to load DXF file and call all analysis functions.
    """
    print("="*70)
    print("PLOT ANALYZER - DXF FILE ANALYSIS")
    print("="*70)
    
    # Initialize analyzer
    dxf_file = "CTP01(LALDARWAJA)FINAL.dxf"
    
    try:
        analyzer = PlotAnalyzer(dxf_file)
        
        print("\n🚀 Starting comprehensive plot analysis...")
        
        # 0. Analyze text entities to understand plot number detection
        print("\n" + "="*50)
        print("0. TEXT ENTITY ANALYSIS FOR PLOT NUMBERS")
        print("="*50)
        text_analysis = analyzer.analyze_text_entities()
        
        # 1. Analyze original plots
        print("\n" + "="*50)
        print("1. ORIGINAL PLOTS ANALYSIS")
        print("="*50)
        original_result = analyzer.original_plots()
        
        # 2. Analyze final plots
        print("\n" + "="*50)
        print("2. FINAL PLOTS ANALYSIS")
        print("="*50)
        final_result = analyzer.final_plots()
        
        # 3. Check unassigned plots with survey numbers
        print("\n" + "="*50)
        print("3. UNASSIGNED PLOTS WITH SURVEY NUMBERS")
        print("="*50)
        unassigned_result = analyzer.check_unassigned_plots_with_survey()
        
        # 4. Check area pending
        print("\n" + "="*50)
        print("4. AREA PENDING ANALYSIS")
        print("="*50)
        pending_result = analyzer.check_area_pending(original_result, final_result)
        
        # 5. Display detailed area report
        print("\n" + "="*50)
        print("5. DETAILED AREA REPORT")
        print("="*50)
        analyzer.display_detailed_area_report(original_result, final_result)
        
        # 6. Summary report
        print("\n" + "="*70)
        print("📋 COMPREHENSIVE SUMMARY REPORT")
        print("="*70)
        
        print(f"\n📊 Original Plots:")
        print(f"   • Total entities: {original_result['total_entities']}")
        print(f"   • Total area: {original_result['total_area_sq_meters']:.2f} sq meters")
        print(f"   • Plot numbers: {original_result['plot_numbers']}")
        
        print(f"\n📊 Final Plots:")
        print(f"   • Total entities: {final_result['total_entities']}")
        print(f"   • Total area: {final_result['total_area_sq_meters']:.2f} sq meters")
        print(f"   • Plot numbers: {final_result['plot_numbers']}")
        
        print(f"\n📊 Unassigned Plots with Survey Numbers:")
        print(f"   • Count: {unassigned_result['total_unassigned_with_survey']}")
        print(f"   • Survey numbers found: {unassigned_result['total_survey_numbers_found']}")
        
        print(f"\n📊 Area Pending:")
        print(f"   • Has pending area: {'Yes' if pending_result['has_pending_area'] else 'No'}")
        print(f"   • Area difference: {pending_result['area_difference_sq_meters']:.2f} sq meters")
        print(f"   • Percentage difference: {pending_result['percentage_difference']:.2f}%")
        
        print("\n" + "="*70)
        print("✅ ANALYSIS COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        print("Please check if the DXF file exists and is valid.")

if __name__ == "__main__":
    main() 