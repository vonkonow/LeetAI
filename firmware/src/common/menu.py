"""
Menu components for the core module.

This module provides functionality for menu navigation and management.
"""

class MenuManager:
    """
    A class for managing menu navigation and state.
    
    Attributes:
        menu: Dictionary containing menu structure and state
        display_manager: DisplayManager instance for UI updates
        dispatch_table: Dictionary mapping action names to functions
    """
    
    def __init__(self, menu_file, display_manager, dispatch_table=None):
        """
        Initialize a new menu manager.
        
        Args:
            menu_file: Path to menu configuration file
            display_manager: DisplayManager instance
            dispatch_table: Dictionary mapping action names to functions
        """
        self.display_manager = display_manager
        self.menu = self._parse_menu(menu_file)
        self.dispatch_table = dispatch_table
    
    def _parse_menu(self, menu_file):
        """
        Parse menu configuration file.
        
        Args:
            menu_file: Path to menu configuration file
            
        Returns:
            dict: Menu structure and state
        """
        txt = []
        jmp = []
        lvl = []
        # Read all lines and strip trailing newlines
        with open(menu_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        # Parse each non-empty line
        for raw in lines:
            if not raw.strip():
                continue
            # Determine indentation level (tabs)
            level = len(raw) - len(raw.lstrip('\t'))
            # Strip leading tabs
            stripped = raw.lstrip('\t')
            # Split text and function on '|'
            if '|' in stripped:
                text, func = stripped.split('|', 1)
            else:
                text, func = stripped, ''
            txt.append(text)
            jmp.append(func)
            lvl.append(level)
        
        # Create navigation arrays in a single pass
        pre = []
        nxt = []
        sel = []
        bck = []
        
        for i in range(len(lvl)):
            # Previous item at same level
            pre.append(i)
            for j in range(i-1, -1, -1):
                if lvl[j] == lvl[i]:
                    pre[i] = j
                    break
            
            # Next item at same level
            nxt.append(i)
            for j in range(i+1, len(lvl)):
                if lvl[j] == lvl[i]:
                    nxt[i] = j
                    break
            
            # Select target
            sel.append(i)
            if i+1 < len(lvl) and lvl[i+1] == lvl[i] + 1:
                sel[i] = i+1
            elif jmp[i]:
                sel[i] = ''
            
            # Back target
            bck.append(i)
            for j in range(i-1, -1, -1):
                if lvl[j] < lvl[i]:
                    bck[i] = j
                    break
        
        return {
            "line": 0,
            "txt": txt,
            "function": jmp,
            "back": bck,
            "previous": pre,
            "next": nxt,
            "select": sel
        }
    
    def handle_rotation(self, rotation):
        """
        Handle menu rotation.
        
        Args:
            rotation: Rotation direction (1 for CW, -1 for CCW)
        """
        if rotation == 1:  # CW
            self.menu["line"] = self.menu["next"][self.menu["line"]]
        elif rotation == -1:  # CCW
            self.menu["line"] = self.menu["previous"][self.menu["line"]]
        self.display_manager.update_menu_text(self.menu["txt"][self.menu["line"]])
    
    def handle_back(self):
        """Handle back button press: go to previous item."""
        idx = self.menu["previous"][self.menu["line"]]
        self.menu["line"] = idx
        self.display_manager.update_menu_text(self.menu["txt"][idx])
    
    def handle_select(self):
        """Handle select button press using dispatch table."""
        if self.menu["select"][self.menu["line"]] != "":
            self.menu["line"] = self.menu["select"][self.menu["line"]]
            self.display_manager.update_menu_text(self.menu["txt"][self.menu["line"]])
        else:
            action = self.menu["function"][self.menu["line"]].strip()
            if self.dispatch_table is not None:
                if ':' in action:
                    func_name, arg = action.split(':', 1)
                    func_name = func_name.strip()
                    func = self.dispatch_table.get(func_name)
                    if func:
                        func(int(arg))
                    else:
                        print(f"Menu action '{func_name}' not found.")
                else:
                    func = self.dispatch_table.get(action)
                    if func:
                        func()
                    else:
                        print(f"Menu action '{action}' not found.")
            else:
                print("No dispatch table provided for menu actions.")
    
    def get_current_text(self):
        """
        Get current menu item text.
        
        Returns:
            str: Current menu item text
        """
        return self.menu["txt"][self.menu["line"]] 