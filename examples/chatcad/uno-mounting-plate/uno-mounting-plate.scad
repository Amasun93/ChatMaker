// ChatMaker ChatCAD Alpha - uno-mounting-plate
$fn = 64;
plate_width = 80.580000;
plate_depth = 65.340000;
plate_thickness = 3.000000;
standoff_height = 5.000000;
standoff_outer_diameter = 7.000000;
hole_diameter = 3.200000;
mounting_holes = [
  [31.750000, 8.890000],
  [31.750000, -19.050000],
  [-19.050000, 24.130000],
  [-20.320000, -24.130000]
];

module mounting_plate() {
  union() {
    translate([-plate_width / 2, -plate_depth / 2, 0])
      cube([plate_width, plate_depth, plate_thickness]);
    for (point = mounting_holes)
      translate([point[0], point[1], plate_thickness])
        difference() {
          cylinder(h=standoff_height, d=standoff_outer_diameter);
          translate([0, 0, -0.01]) cylinder(h=standoff_height + 0.02, d=hole_diameter);
        }
  }
}

mounting_plate();
