from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopAbs import TopAbs_COMPOUND
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Reader, StlAPI_Writer
from OCC.Core.BRep import BRep_Builder
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.IGESControl import IGESControl_Reader, IGESControl_Writer
from OCC.Core.STEPControl import STEPControl_Reader, STEPControl_Writer, STEPControl_AsIs
from OCC.Core.Interface import Interface_Static_SetCVal
from OCC.Core.IFSelect import IFSelect_RetDone, IFSelect_ItemsByEntity
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.XCAFDoc import (XCAFDoc_DocumentTool_ShapeTool,
                              XCAFDoc_DocumentTool_ColorTool,
                              XCAFDoc_ColorGen,
                              XCAFDoc_ColorSurf,
                              XCAFDoc_ColorCurv)
from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
from OCC.Core.TDF import TDF_LabelSequence, TDF_Label, TDF_Tool, TDF_ChildIterator
from OCC.Core.TDataStd import TDataStd_Name, TDataStd_Name_GetID
from OCC.Core.TCollection import TCollection_ExtendedString, TCollection_AsciiString
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.XCAFDoc import XCAFDoc_Location, XCAFDoc_Location_GetID

from OCC.Extend.TopologyUtils import TopologyExplorer

OCAF_KEEP_PLACEMENT = True
VERBOSE = False


from OCC.Display.SimpleGui import init_display
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox

display, start_display, add_menu, add_function_to_menu = init_display()

class ImportOCAF:
    def __init__(self, h, name):
        self.pDoc = h
        #self.doc = d
        self.merge = True
        self.default_name = name
        self.aShapeTool = XCAFDoc_DocumentTool_ShapeTool(self.pDoc.Main())
        self.aColorTool = XCAFDoc_DocumentTool_ColorTool(self.pDoc.Main())
        self.myRefShapes = []

    def loadShapes_first(self):
        lValue = []
        self.myRefShapes = []
        self.loadShapes(self.pDoc.Main(), TopLoc_Location(),
                        self.default_name, "", False, lValue);
        lValue = []

    def setMerge(self, merge):
        """ merge: a boolean
        """
        self.merge = merge

    def loadShapes(self, label, loc, defaultname, assembly, isRef, lValue):
        """const TDF_Label& label, const TopLoc_Location& loc,
           const std::string& defaultname, const std::string& assembly,
           bool isRef,
          std::vector<App::DocumentObject*>& lValue)
        """
        hash_ = 0

        aShape = TopoDS_Shape()
        localValue = []
        if self.aShapeTool.GetShape(label, aShape):
            hash_ = hash(aShape)

        name = TDataStd_Name()
        part_name = defaultname
        if label.FindAttribute(TDataStd_Name_GetID(), name):
            part_name = name.Get().PrintToString()
            if part_name == "" or part_name.isspace():
                part_name = defaultname
        
        part_loc = loc
        hLoc = XCAFDoc_Location()
        if label.FindAttribute(XCAFDoc_Location_GetID(), hLoc):
            if isRef:
                part_loc = part_loc * hLoc.Get()
            else:
                part_loc = hLoc.Get()

        if VERBOSE:
            print(hash_,
                  part_name,
                  self.aShapeTool.IsTopLevel(label),
                  self.aShapeTool.IsAssembly(label),
                  self.aShapeTool.IsShape(label),
                  self.aShapeTool.IsCompound(label),
                  self.aShapeTool.IsSimpleShape(label),
                  self.aShapeTool.IsFree(label),
                  self.aShapeTool.IsReference(label),
                  self.aShapeTool.IsComponent(label),
                #  self.aShapeTool.IsSubShape(label)
                )

        if OCAF_KEEP_PLACEMENT:
            asm_name = part_name
        else:
            asm_name = assembly
            if self.aShapeTool.IsAssembly(label):
                asm_name = part_name
    
        ref = TDF_Label()
        if (self.aShapeTool.IsReference(label) and
            self.aShapeTool.GetReferredShape(label, ref)):
            self.loadShapes(ref, part_loc, part_name, asm_name, True, lValue)
    
        if (isRef or hash_ not in self.myRefShapes):
            aShape = TopoDS_Shape()
            if (isRef and self.aShapeTool.GetShape(label, aShape)):
                self.myRefShapes.append(hash(aShape))
                display.DisplayShape(aShape)

            if (self.aShapeTool.IsSimpleShape(label) and
                (isRef or self.aShapeTool.IsFree(label))):
                if not asm_name is None:
                    part_name = asm_name
                if isRef:
                    self.createShape(label, loc, part_name, lValue, self.merge)
                else:
                    self.createShape(label, part_loc, part_name, localValue, self.merge)
            else:
                if self.aShapeTool.IsSimpleShape(label):
                    print("on returne !!")
                    return
                # This is probably an Assembly let's try to create a Compound with
                # the name
                it = TDF_ChildIterator(label)
                while it.More():
                    if isRef:
                        self.loadShapes(it.Value(), part_loc, part_name, asm_name,
                                        False, localValue)
                    else:
                        self.loadShapes(it.Value(), part_loc, part_name, asm_name,
                                        isRef, localValue)
                    it.Next()
    
                if len(localValue) > 0:
                    pass

    #             if (!localValue.empty()) {
    #                 if (aShapeTool->IsAssembly(label)) {
    #                     App::Part *pcPart = NULL;
    #                     pcPart = static_cast<App::Part*>(doc->addObject("App::Part",asm_name.c_str()));
    #                     pcPart->Label.setValue(asm_name);
    #                     pcPart->addObjects(localValue);

    #                     // STEP reader is now a hierarchical reader. Node and leaf must have
    #                     // there local placement updated and relative to the STEP file content
    #                     // standard FreeCAD placement was absolute we are now moving to relative

    #                     gp_Trsf trf;
    #                     Base::Matrix4D mtrx;
    #                     if (part_loc.IsIdentity())
    #                         trf = part_loc.Transformation();
    #                     else
    #                         trf = TopLoc_Location(part_loc.FirstDatum()).Transformation();
    #                     Part::TopoShape::convertToMatrix(trf, mtrx);
    #                     Base::Placement pl;
    #                     pl.fromMatrix(mtrx);
    #                     pcPart->Placement.setValue(pl);

    #                     lValue.push_back(pcPart);
    #                 }
    #             }
    #         }
    #     }
    # }

    def createShape(self, label, loc, name, lValue, merge):
        """
        const TDF_Label& label
        const TopLoc_Location& loc
        const std::string& name
        std::vector<App::DocumentObject*>& lValue
        bool merge
        """
        print("Create shape with name", name)
        aShape = self.aShapeTool.GetShape(label)
        colors = []

        if (not aShape.IsNull() and aShape.ShapeType() == TopAbs_COMPOUND):
            print("dedans")
            localValue = []
            if merge:
                builder = BRep_Builder()
                comp = TopoDS_Compound()
                builder.MakeCompound(comp)
                topo = TopologyExplorer(aShape)
                
                ctSolids = ctShells = ctEdges = ctVertices = False
                for s in topo.solids():
                    if not s.IsNull():
                        builder.Add(comp, s)
                        ctSolids = True
                for sh in topo.shells():
                    if not sh.IsNull():
                        builder.Add(comp, sh)
                        ctShells = True
                for e in topo.edges():
                    if not e.IsNull():
                        builder.Add(comp, e)
                        ctEdges = True
                for v in topo.vertices():
                    if not v.IsNull():
                        builder.Add(comp, v)
                        ctVertices = True
                # Ok we got a Compound which is computed
                # Just need to add it to a Part::Feature and push it to lValue
                if (not comp.IsNull() and (ctSolids or ctShells or ctEdges or ctVertices)):
    #                 Part::Feature* part = static_cast<Part::Feature*>(doc->addObject("Part::Feature"));
    #                 // Let's allocate the relative placement of the Compound from the STEP file
    #                 gp_Trsf trf;
    #                 Base::Matrix4D mtrx;
    #                 if ( loc.IsIdentity() )
    #                      trf = loc.Transformation();
    #                 else
    #                      trf = TopLoc_Location(loc.FirstDatum()).Transformation();
                    if loc.IsIdentity():
                        trf = loc.Transformation()
                    else:
                        trf = TopLoc_Location(loc.FirstDatum()).Transformation()
    #                 Part::TopoShape::convertToMatrix(trf, mtrx);
    #                 Base::Placement pl;
    #                 pl.fromMatrix(mtrx);
    #                 part->Placement.setValue(pl);
    #                 if (!loc.IsIdentity())
    #                     part->Shape.setValue(comp.Moved(loc));
    #                 else
    #                     part->Shape.setValue(comp);
                    if not loc.IsIdentity():
                        comp = comp.Moved(loc)
    #                 part->Label.setValue(name);
    #                 lValue.push_back(part);
                    self.lValue.append(comp)
                    print("on y est!!")
                    display.DisplayShape(comp)
    #             }
    #         }

            else:
                for s in topo.solids():
                    self.another_create_shape(s, loc, name, localValue)
                for sh in topo.shells():
                    self.another_create_shape(sh, loc, name, localValue)

            if len(localValue) > 0 and not merge:
                # TODO : un truc qui cloche
                self.lValue.append(new_part)
            if ctSolids or ctShells:
                return 

        elif (not aShape.IsNull()):
            print("dehors")
            self.another_create_shape(aShape, loc, name, lValue)
        elif aShape.IsNull():
            raise AssertionError("Shape is Null")

    def another_create_shape(self, aShape, loc, name, lvalue):
        """
        const TopoDS_Shape& aShape,
        const TopLoc_Location& loc,
        const std::string& name,
        std::vector<App::DocumentObject*>& lvalue
        """
        print('on y est')

        if not loc.IsIdentity():
            aShape = aShape.Moved(loc)  # TODO check this line

        lvalue.append(aShape)

        aColor = Quantity_Color()  # default color

        if (self.aColorTool.GetColor(aShape, XCAFDoc_ColorGen, aColor) or
            self.aColorTool.GetColor(aShape, XCAFDoc_ColorSurf, aColor) or
            self.aColorTool.GetColor(aShape, XCAFDoc_ColorCurv, aColor)):
            r = aColor.Red()
            g = aColor.Green()
            b = aColor.Blue()
            colors = []
            colors.append([r, g, b])

        display.DisplayColoredShape(aShape, color = aColor)

        found_face_color = False
        faceColors = {}
        topo = TopologyExplorer(aShape)
        for f in topo.faces():
            if (self.aColorTool.GetColor(f, XCAFDoc_ColorGen, aColor) or
                self.aColorTool.GetColor(f, XCAFDoc_ColorSurf, aColor) or
                self.aColorTool.GetColor(f, XCAFDoc_ColorCurv, aColor)):
                r = aColor.Red()
                g = aColor.Green()
                b = aColor.Blue()
                faceColors[f] = Quantity_Color(r, g, b, Quantity_TOC_RGB)
                found_face_color = True

        if found_face_color:
            print("Found Face COLOr !!!!")
            for popo in faceColors:
                display.DisplayColoredShape(popo, color=faceColors[popo])

    # void ImportOCAFCmd::applyColors(Part::Feature* part, const std::vector<App::Color>& colors)
    # {
    #     partColors[part] = colors;
    # }
import os
filename = "../../demos/assets/models/pm25_iw_214.stp"
if not os.path.isfile(filename):
    raise FileNotFoundError("%s not found." % filename)

doc = TDocStd_Document(TCollection_ExtendedString("pythonocc-doc"))
step_reader = STEPCAFControl_Reader()
step_reader.SetColorMode(True)
step_reader.SetLayerMode(True)
step_reader.SetNameMode(True)
step_reader.SetMatMode(True)
status = step_reader.ReadFile(filename)
if status == IFSelect_RetDone:
    step_reader.Transfer(doc)
print('ok')
# and now we parse the document
# create the importer
i = ImportOCAF(doc, "pythonocc-doc")
i.loadShapes_first()
start_display()
