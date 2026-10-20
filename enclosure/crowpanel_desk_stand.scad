// ═══════════════════════════════════════════════════════════════════════════
// CrowPanel 7" Desk Stand: housing + 20° stand + top-right volume knob
// For: Elecrow CrowPanel 7.0" Basic (ESP32-S3, DIS08070H) board V3.0, as shipped
//      (with its black front frame). Sizes taken from Elecrow's official STEP
//      "3D_File_CrowPanel_7.0-ESP32_HMI-3.0.stp".
// Knob: KY-040 / EC11 rotary encoder module (M7x0.75 bushing, 6 mm shaft)
// Cable: right-angle USB-C, routed behind the panel, out the back between the legs
//
// VERSION 1.0.0 (2026-10-18), MIT license
// https://github.com/ananthrajah/crowpanel-ha-desk-panel
//
// Parts (set `part`):
//   shell  : front bezel + walls. Print FRONT FACE DOWN, no supports.
//   back   : back cover. Print OUTSIDE FACE DOWN, no supports.
//   stand  : 2-leg stand. Print FLAT (mounting face) DOWN, no supports.
//   knob   : knob cap. Print TOP DOWN, no supports.
//   assembly / exploded : preview only.
// Hardware: 8x M3 heat-set inserts (4.0 mm hole, 4-5.7 mm long), 4x M3x8 countersunk
//           (back cover), 4x M3x8 pan/button head (stand), 4x bumpon feet (8-10 mm, optional)
// ═══════════════════════════════════════════════════════════════════════════

part = "assembly"; // [shell, back, stand, knob, assembly, exploded]

/* [Stand] */
tilt = 20;          // lean back from vertical (degrees)
leg_reach = 78;     // how far the legs reach back along the desk (mm)
leg_x = 62;         // legs at ±leg_x from centre (mm)

/* [Knob] */
knob_x = 80;        // knob position, mm right of centre (as seen from the front)
knob_d = 28;        // knob cap diameter
knob_h = 16;        // knob cap height
shaft = "knurled";  // [knurled, D] KY-040 shafts are usually knurled 6 mm
shaft_d = 6.0;

/* [Fit] */
clr = 0.35;         // clearance around the panel (each side)
insert_d = 4.0;     // heat-set insert hole
show_panel = true;  // dummy panel in assembly preview

/* [Hidden] */
$fn = 64;
// ── CrowPanel 7.0 V3.0 (from Elecrow STEP). Origin = board centre, front frame face.
pw = 184.0;  ph = 108.4;        // outline
pd_pcb = 12.55;                 // depth to PCB back
pd = 13.7;                      // depth incl. corner screw heads
win = [-82.66, 82.64, -52.26, 50.14];   // front frame window (x0,x1,y0,y1), viewer coords
// features, viewer coords (x right, y up), depth from front face
usb   = [-86.7, -0.7, 8.1];    // left edge, USB-C (viewer left)
btnL  = [-29.0, 9.8];          // left-edge button: y, depth
btnB  = [45.06, 9.8];          // bottom-edge button: x, depth
tf    = [-64.5, -51.6, 8.4];   // bottom-edge TF card: x0, x1, depth centre
hy_conn = [[-66.2,-45.2],[-17.9,-5.9],[14.1,26.1],[46.1,58.1]]; // top-edge connectors (x ranges)

// ── housing
wall = 2.4;  front = 2.0;
side_ch = 15;      // left/right inner channel (USB plug on the left)
top_ch  = 18;      // top chamber (HY2.0 plugs + knob module)
rear_gap = 7.5;    // behind the PCB: cable, screw heads, pads
back_t = 2.4;
r_out = 6;

xi = pw/2 + clr + side_ch;            // inner half width
yi0 = -(ph/2 + clr);                  // inner bottom
yi1 = ph/2 + clr + top_ch;            // inner top
zi1 = front + pd + clr + rear_gap;    // inner back (= back cover inner face)
D   = zi1 + back_t;                   // total depth
xo = xi + wall; yo0 = yi0 - wall; yo1 = yi1 + wall;
W = 2*xo; H = yo1 - yo0;

boss_d = 8.6;
boss_xy = [for (sx=[-1,1], y=[yi1-6.5, yi0+6.5]) [sx*(xi-6.5), y]];
pad_xy  = [[-70,25],[70,25],[-70,-30],[70,-30],[0,30]];
stand_xy = [[-50,8],[50,8],[-50,-38],[50,-38]];
stand_top = 22;     // stand plate top edge (y)
stand_t = 5;

kz = (front + zi1)/2;
feet_x = [[-100,-70],[54,100]];   // wedge feet under the bottom (viewer x ranges, clear of TF + button)  // knob axis depth (middle of the inner space)

// viewer x → model x (model is built looking at the front face from -z,
// so viewer-right is model -x)
function fx(x) = -x;

// ═════════════════════ helpers
module rbox(x0,x1,y0,y1,z0,z1,r) {
  translate([0,0,z0]) linear_extrude(z1-z0)
    hull() for (x=[x0+r,x1-r], y=[y0+r,y1-r]) translate([x,y]) circle(r);
}
module slot2d(l, w) { hull() for (s=[-1,1]) translate([s*(l-w)/2,0]) circle(d=w); }

// ═════════════════════ SHELL
module shell() {
  difference() {
    union() {
      difference() {
        rbox(-xo, xo, yo0, yo1, 0, D, r_out);
        // inner cavity
        rbox(-xi, xi, yi0, yi1, front, D+1, max(r_out-wall, 1));
      }
      // bosses for back-cover screws
      for (p = boss_xy) translate([p[0], p[1], front]) cylinder(d=boss_d, h=zi1-front);
      // side locating ribs (skip USB plug and left button)
      for (sx=[-1,1]) {
        segs = sx == -1 ? [[-46,-36],[-22,-10],[10,46]]          // viewer-left wall (USB side)
                        : [[-46,-14],[14,46]];
        for (s = segs)
          translate([fx(sx*(pw/2+clr)) + (fx(sx) > 0 ? 0 : -2), s[0], front])
            cube([2, s[1]-s[0], pd_pcb]);
      }
      // top stops (between the top-edge connectors)
      for (x = [-80, -31, 5, 36, 76]) translate([fx(x)-3, ph/2+clr, front]) cube([6, 2.5, pd_pcb]);
      // wedge feet under the bottom wall: front edge on the desk, keeps it from tipping forward
      for (f = feet_x) intersection() {
        translate([fx(f[1]), yo0-12, 0]) cube([f[1]-f[0], 12.01, D]);
        desk_keep();
      }
      // left-button pin guide
      // (a solid web down to the front plate so it prints without supports)
      translate([fx(-(pw/2+clr+0.5)), btnL[0]-2.75, front]) cube([side_ch-0.5, 5.5, btnL[1]+2.75]);
    }
    // screen opening with 45° chamfer on the front
    hull() {
      translate([0,0,-0.01]) rbox(fx(win[1])-0.4-1.2, fx(win[0])+0.4+1.2, win[2]-0.4-1.2, win[3]+0.4+1.2, -0.01, 0.01, 2.5);
      rbox(fx(win[1])-0.4, fx(win[0])+0.4, win[2]-0.4, win[3]+0.4, 1.2, 1.21, 1.5);
    }
    rbox(fx(win[1])-0.4, fx(win[0])+0.4, win[2]-0.4, win[3]+0.4, 1.0, front+1, 1.5);
    // insert holes
    for (p = boss_xy) translate([p[0], p[1], zi1-6]) cylinder(d=insert_d, h=7);
    // knob: M7 bushing hole through the top wall + seat for the encoder body
    translate([fx(knob_x), yi1-0.01, kz]) rotate([-90,0,0]) {
      cylinder(d=7.4, h=wall+1);
      translate([0,0,-1]) cylinder(d=15, h=1.8);  // thins the wall to 1.6 mm
    }
    // left-button pinhole (through wall + guide)
    translate([fx(-(xo+1)), btnL[0], front+btnL[1]]) rotate([0,-90,0]) cylinder(d=2.2, h=side_ch+wall+2);
    // bottom-button pinhole
    translate([fx(btnB[0]), yo0-1, front+btnB[1]]) rotate([-90,0,0]) cylinder(d=2.2, h=wall+2);
    // TF card slot
    translate([fx(tf[1]), yo0-1, front+tf[2]-2.5]) cube([tf[1]-tf[0], wall+2, 5]);
    // bumpon recesses in the wedge feet (desk face)
    for (f = feet_x) let(xm=(f[0]+f[1])/2, zc=D*0.45)
      translate([fx(xm), yo0 - (D-zc)*tan(tilt), zc]) rotate([90-tilt,0,0]) translate([0,0,-1]) cylinder(d=10.5, h=2);
    // bottom vents
    for (x=[-30,-10,10,30]) translate([fx(x), yo0+wall/2, front+16]) cube([14, wall+2, 3], center=true);
  }
}

// ═════════════════════ BACK COVER  (z from zi1 to D, outside face = z=D)
module back_cover() {
  g = 0.25; // fit gap to the walls
  difference() {
    union() {
      rbox(-xi+g, xi-g, yi0+g, yi1-g, zi1, D, max(r_out-wall-g, 1));
      // stiffening rim
      difference() {
        rbox(-xi+g, xi-g, yi0+g, yi1-g, zi1-3, zi1, max(r_out-wall-g,1));
        rbox(-xi+g+1.6, xi-g-1.6, yi0+g+1.6, yi1-g-1.6, zi1-4, zi1+1, 1);
        // rim gaps for bosses
        for (p = boss_xy) translate([p[0],p[1],zi1-4]) cylinder(d=boss_d+1.2, h=5);
      }
      // pads that hold the panel against the bezel (0.2 mm preload)
      for (p = pad_xy) translate([p[0], p[1], front + pd_pcb - 0.2]) cylinder(d=10, h=zi1 - (front + pd_pcb - 0.2));
    }
    // countersunk M3 to the shell bosses
    for (p = boss_xy) translate([p[0], p[1], zi1-1]) {
      cylinder(d=3.4, h=10);
      translate([0,0,D-zi1+1-1.8]) cylinder(d1=3.4, d2=6.6, h=1.8+0.01);
    }
    // stand screws (heads inside)
    for (p = stand_xy) translate([fx(p[0]), p[1], zi1-1]) cylinder(d=3.4, h=10);
    // cable exit, bottom centre
    translate([0, yi0+10, zi1-4]) linear_extrude(10) rotate(90) slot2d(16, 12);
    // knock-out for a second exit behind the USB plug (punch out if needed)
    translate([fx(-(pw/2+clr+side_ch/2)), 0, zi1-4]) linear_extrude(D-zi1+4-0.6) rotate(90) slot2d(26, 9);
    // vents (top area, behind the connectors)
    for (x=[-55,-20,15,50], y=[44,52,60]) translate([x, y, zi1-4]) linear_extrude(10) slot2d(26, 3);
  }
}

// ═════════════════════ STAND (attached behind the back cover)
// height above desk, in housing coords, desk touches the back-bottom edge
function h_desk(y,z) = cos(tilt)*(y - yo0) - sin(tilt)*(z - D);
module desk_keep() {   // half-space above the desk, as a big block
  big = 600;
  translate([0, yo0, D]) rotate([-tilt,0,0]) translate([-big/2, 0, -big/2]) cube(big);
}
module stand() {
  C = [yo0 + leg_reach*sin(tilt), D + leg_reach*cos(tilt)];
  intersection() {
    difference() {
      union() {
        // mounting plate
        rbox(-leg_x-6, leg_x+6, yo0-2, stand_top, D, D+stand_t, 5);
        for (sx=[-1,1]) {
          // leg
          translate([sx*leg_x - 3, 0, 0]) rotate([90,0,90]) linear_extrude(6)
            polygon([[yo0-20, D], [stand_top-4, D], [C[0]+2, C[1]], [yo0-20, C[1]+5]]);
          // foot shoe (wider, sits on the desk)
          translate([sx*leg_x - 7, 0, 0]) rotate([90,0,90]) linear_extrude(14)
            polygon([[yo0-20, D], [yo0+7, D], [C[0]+2+7*cos(tilt), C[1]-7*sin(tilt)], [C[0]+2, C[1]], [yo0-20, C[1]+5]]);
        }
      }
      // insert holes (from the mounting face)
      for (p = stand_xy) translate([fx(p[0]), p[1], D-1]) cylinder(d=insert_d, h=stand_t);
      // cable notch
      translate([-8, yo0-5, D-1]) cube([16, 5+ (yi0+18) - yo0, stand_t+2]);
      // bumpon recesses on the shoes
      for (sx=[-1,1], t=[0.25, 0.85]) {
        p = [yo0 + t*leg_reach*sin(tilt), D + t*leg_reach*cos(tilt)];
        translate([sx*leg_x, p[0], p[1]]) rotate([90-tilt,0,0]) translate([0,0,-1]) cylinder(d=10.5, h=2);
      }
      // lightening window in the plate
      translate([0, -5, D-1]) linear_extrude(stand_t+2) offset(r=4) square([2*leg_x-60, 30], center=true);
    }
    desk_keep();
  }
}

// ═════════════════════ KNOB
module knob() {
  difference() {
    union() {
      cylinder(d=knob_d, h=knob_h-1.5);
      translate([0,0,knob_h-1.5]) cylinder(d1=knob_d, d2=knob_d-3, h=1.5);
    }
    // grip flutes
    for (a=[0:360/30:359]) rotate(a) translate([knob_d/2+0.6, 0, -1]) cylinder(d=2.4, h=knob_h+2, $fn=16);
    // skirt recess (hides the nut)
    translate([0,0,-0.01]) cylinder(d=13, h=3.5);
    // shaft bore
    if (shaft == "D") translate([0,0,-0.01]) intersection() {
      cylinder(d=shaft_d+0.2, h=12);
      translate([-(shaft_d+1)/2, -(shaft_d+1)/2 + (shaft_d+0.2 - 4.7), 0]) cube([shaft_d+1, shaft_d+1, 12]);
    } else translate([0,0,-0.01]) cylinder(d=shaft_d+0.05, h=12, $fn=40);
    // indicator dot
    translate([0, knob_d/2-4.5, knob_h-0.6]) cylinder(d=2.5, h=1);
  }
}

// ═════════════════════ dummy panel (preview only)
module panel_dummy() {
  color("#222") translate([0,0,front]) difference() {
    rbox(-pw/2, pw/2, -ph/2, ph/2, 0, pd_pcb, 1);
    translate([0,0,-0.1]) rbox(fx(win[1]), fx(win[0]), win[2], win[3], 0, 1.6, 0.5);
  }
  color("#3a7bd5") translate([0,0,front+1.6]) rbox(fx(76.9), fx(-76.9), -44.5, 41.1, -0.01, 0.2, 0.2);
}
module ky040() {
  color("#1565c0") translate([fx(knob_x), yi1-1.6-6.5-1.6, kz]) rotate([-90,0,0]) {
    translate([-24, -9.5, 0]) cube([30, 19, 1.6]);
    color("silver") translate([0,0,1.6]) { translate([-6,-6,0]) cube([12,12,6.5]); cylinder(d=7, h=6.5+7); cylinder(d=6, h=6.5+20); }
  }
}

module assembled(ex=0) {
  shell();
  if (show_panel) panel_dummy();
  ky040();
  translate([0,0,ex]) color("#555") back_cover();
  translate([0,0,2*ex]) color("#444") stand();
  translate([fx(knob_x), yi1+wall+0.5+ex/2, kz]) rotate([-90,0,0]) color("#888") knob();
}

if (part == "shell") shell();
else if (part == "back") translate([0,0,D]) mirror([0,0,1]) back_cover();       // outside face down
else if (part == "stand") translate([0,0,-D]) stand();                          // mounting face down
else if (part == "knob") translate([0,0,knob_h]) mirror([0,0,1]) knob();         // top down
else if (part == "exploded") rotate([90+tilt,0,180]) assembled(40);
else rotate([90+tilt,0,180]) assembled(0);
