#!/usr/bin/env python
import time
import math
import wx
import wx.lib.plot as plot
import threading
import socket
import struct

class RegionEditor(wx.Frame):
    def __init__(self, parent):
        """Create the main frame to hold the Region Editor functionality."""
        wx.Frame.__init__(self, parent, title="Region Editor")
        
        # Status bar
        self.CreateStatusBar()
        
        # Menu bar
        filemenu = wx.Menu()    # Create "File" menu tab
        menuSave = filemenu.Append(wx.ID_SAVE, "&Save", "Save the current map")
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit", "Terminate the program")
        editmenu = wx.Menu()    # Create "Edit" menu tab
        menuUndo = editmenu.Append(wx.ID_UNDO, "&Undo", "Revert the previous action")
        menuRedo = editmenu.Append(wx.ID_REDO, "&Redo", "Revert the previously undone action")
        helpmenu = wx.Menu()    # Create "Help" menu tab
        menuAbout = helpmenu.Append(wx.ID_ABOUT, "&About", "Information about the program")
        self.Bind(wx.EVT_MENU, self.OnMenuSave, menuSave)   # Make menu items call functions
        self.Bind(wx.EVT_MENU, self.OnMenuExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnMenuUndo, menuUndo)
        self.Bind(wx.EVT_MENU, self.OnMenuRedo, menuRedo)
        self.Bind(wx.EVT_MENU, self.OnMenuAbout, menuAbout)
        menubar = wx.MenuBar()  # Create menu bar with tabs
        menubar.Append(filemenu, "&File")
        menubar.Append(editmenu, "&Edit")
        menubar.Append(helpmenu, "&Help")
        self.SetMenuBar(menubar)
        
        # Create control sidebar and map drawing panels
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sidebar = ControlSidebar(self)
        self.canvas = MapCanvas(self)
        sizer.Add(self.sidebar, 0, wx.EXPAND)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)
        
        self.Show(True)
    
    def OnMenuSave(self, event):
        # TODO
        pass
    
    def OnMenuExit(self, event):
        # TODO: Check if map is saved, etc
        self.Close(True)
    
    def OnMenuUndo(self, event):
        # TODO
        pass
    
    def OnMenuRedo(self, event):
        # TODO
        pass
    
    def OnMenuAbout(self, event):
        # TODO
        pass


class ControlSidebar(wx.Panel):
    def __init__(self, parent):
        """Create the sidebar that contains all control buttons."""
        wx.Panel.__init__(self, parent, size=(150, 400), style = wx.SUNKEN_BORDER)
        self.parent = parent
        
        # Control buttons
        rowSizer = wx.BoxSizer(wx.VERTICAL)     # Top-level sizer
        visSizer = wx.BoxSizer(wx.HORIZONTAL)   # Vicon and camera display row
        polySizer = wx.BoxSizer(wx.HORIZONTAL)  # Region creation row
        self.toggleVicon = wx.ToggleButton(self, label='V', size=(50, 50))
        self.buttonCamera = wx.Button(self, label='C', size=(50, 50))
        self.toggleSquare = wx.ToggleButton(self, label='S', size=(50, 50))
        self.togglePolygon = wx.ToggleButton(self, label='P', size=(50, 50))
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggleVicon, self.toggleVicon)
        self.Bind(wx.EVT_BUTTON, self.OnButtonCamera, self.buttonCamera)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggleSquare, self.toggleSquare)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnTogglePolygon, self.togglePolygon)
        visSizer.Add(self.toggleVicon, proportion=0)
        visSizer.Add(self.buttonCamera, proportion=0)
        polySizer.Add(self.toggleSquare, proportion=0)
        polySizer.Add(self.togglePolygon, proportion=0)
        rowSizer.Add(visSizer, 1)
        rowSizer.Add(polySizer, 1)
        self.SetSizerAndFit(rowSizer)
    
    def OnToggleVicon(self, event):
        # Switch Vicon streaming on or off based on state of toggle button
        if self.toggleVicon.GetValue():
            self.parent.canvas.listener.start()
        else:
            self.parent.canvas.listener.stop()
    
    def OnButtonCamera(self, event):
        # TODO
        pass
    
    def OnToggleSquare(self, event):
        self.clearMapToggles(self.toggleSquare)
    
    def OnTogglePolygon(self, event):
        self.clearMapToggles(self.togglePolygon)
    
    def clearMapToggles(self, toggleOn):
        """Clear all the other map-feature toggle buttons.
        
        toggleOn - Toggle button object to turn back on.
        """
        self.toggleSquare.SetValue(False)
        self.togglePolygon.SetValue(False)
        toggleOn.SetValue(True)


class MapCanvas(plot.PlotCanvas):
    def __init__(self, parent):
        """Create the main map area for drawing regions."""
        
        # Initialize member parameters
        self.parent = parent
        self.leftClickPt = (0.0, 0.0)       # Location of last left downclick
        self.rightClickPt = (0.0, 0.0)      # Location of last right downclick
        self.canvasSize = (800.0, 400.0)    # (pixels)
        self.mapBound = [(-3.0, 9.0), (-3.0, 3.0)]  # Map boundaries [(xmin, xmax), (ymin, ymax)] (m)
        self.tolerance = (5.0 / self.canvasSize[0]) * \
            (self.mapBound[0][1] - self.mapBound[0][0]) # Distance to consider as "same point" (m)
        self.polyVerts = []                 # Keeps points for region creation
        
        # Parent constructor
        plot.PlotCanvas.__init__(self, parent, size=self.canvasSize, style = wx.SUNKEN_BORDER)
        
        # Set up canvas for plotting
        self.SetBackgroundColour('WHITE')
        self.SetInitialSize(size=self.canvasSize)
        emptyMarkers = plot.PolyMarker([])
        gc = plot.PlotGraphics([emptyMarkers])
        self.Draw(gc, xAxis=self.mapBound[0], yAxis=self.mapBound[1])
        self.listener = ViconMarkerListener(self)
        
        # Subscribe to mouse events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnMouseRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnMouseRightUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
    
    def OnMouseLeftDown(self, event):
        """Save the left click point so it can be used later."""
        self.leftClickPt = self.PositionScreenToUser(event.GetPosition())
    
    def OnMouseLeftUp(self, event):
        """Perform appropriate action based on current mode of operation."""
        # Get click position
        pt = self.PositionScreenToUser(event.GetPosition())
        
        # Creating a square region
        if self.parent.sidebar.toggleSquare.GetValue():
            # Making the second corner of a square
            if self.polyVerts:
                # Create a square between previous click and new click
                x1, y1 = self.polyVerts[0]
                x2, y2 = pt
                self.DrawRegion([(x1, y1), (x1, y2), (x2, y2), (x2, y1)])
                self.polyVerts = []
            # Single click on a spot
            elif math.sqrt((pt[0] - self.leftClickPt[0]) ** 2 + \
                    (pt[1] - self.leftClickPt[1]) ** 2) < self.tolerance:
                # Save point as first corner of square
                self.polyVerts.append(pt)
            # Dragged from one spot to another
            else:
                # Create a square between the downclick and upclick
                x1, y1 = self.leftClickPt
                x2, y2 = pt
                self.DrawRegion([(x1, y1), (x1, y2), (x2, y2), (x2, y1)])
                self.polyVerts = []
        
        # Creating a polygonal region
        elif self.parent.sidebar.togglePolygon.GetValue():
            pass
    
    def OnMouseRightDown(self, event):
        """Save the right click point so it can be used later."""
        self.rightClickPt = self.PositionScreenToUser(event.GetPosition())
        # TODO: Possibly clear polyVerts
    
    def OnMouseRightUp(self, event):
        # TODO
        pass
    
    def OnMouseWheel(self, event):
        # TODO
        pass
    
    def DrawMarkers(self, pos):
        """Draw markers at specified global positions.
        
        pos - list of tuples containing positions of markers in meters [(x, y), ...]
        """
        marker = plot.PolyMarker(pos)
        gc = plot.PlotGraphics([marker])
        self.Draw(gc, xAxis=(-3, 9), yAxis=(-3, 3))
    
    def DrawRegion(self, verts):
        """Draw a region contained by the specified points.
        
        verts - List of tuples containing points that enclose the region.
                [(x1, y1), (x2, y2), ...]
                The list shall not loop back to the first point.
        """
        # Plot all lines
        # TODO: Get fill, may need to changes from wx.lib.plot library
        verts.append(verts[0])
        lines = plot.PolyLine(verts)
        gc = plot.PlotGraphics([lines])
        self.Draw(gc, xAxis=(-3, 9), yAxis=(-3, 3))
    
    # TODO: OnResize
    #       Change mapBoundaries and canvasSize
    #       Recalculate tolerance
    #       Redraw everything only once (not continuously)


class ViconMarkerListener(threading.Thread):
    def __init__(self, parent):
        """Create the a socket to receive Vicon data.
        
        parent - Panel containing the drawing canvas on which to plot markers
        """
        super(ViconMarkerListener, self).__init__()
        self.canvas = parent
        self.addr = ("0.0.0.0", 7500)
        self.bufsize = 65536
        self.udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.lock = threading.Lock()
        self.close = threading.Event()
    
    def run(self):
        """Open the socket to start communication. Process messages."""
        # Open socket for communication
        self.udpSock.bind(self.addr)
        
        # Receive communication until stopped
        while not self.close.isSet():
            self.lock.acquire()
            data = self.udpSock.recv(self.bufsize)
            self.ProcessData(data)
            self.lock.release()
            time.sleep(0.05)
        
        # Close socket
        self.udpSock.close()
    
    def stop(self):
        """Close the socket to end UDP communication."""
        self.close.set()

    # Deserialize and save data
    def ProcessData(self, data):
        """Extract marker positions and pass them on to be mapped.
        
        data - Byte array encoded from multiple pairs of doubles [x1 y1 ...]
        """
        # Check for valid data (not null or incomplete)
        print len(data)
        if data and len(data)%16 == 0:
            pos = []
            for i in range(0, len(data), 16):
                x, y = struct.unpack('dd', data[i:i+16])
                pos.append((x, y))
                if i < 160:
                    print x,y
            self.canvas.DrawMarkers(pos)    # Plot Vicon markers


if __name__ == "__main__":
    app = wx.App(False)
    frame = RegionEditor(None)
    app.MainLoop()