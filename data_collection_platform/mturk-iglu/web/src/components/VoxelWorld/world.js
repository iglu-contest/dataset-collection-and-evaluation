/*
Copyright (c) Facebook, Inc. and its affiliates.

This is taken directly from (with a few modifications):
https://github.com/facebookresearch/droidlet/blob/yuxuans/unify_dashboard/droidlet/dashboard/web/src/components/VoxelWorld/world.js
*/
var createGame = require("voxel-engine");
var highlight = require("voxel-highlight");
var player = require("voxel-player");
var voxel = require("voxel");
var extend = require("extend");
var fly = require("voxel-fly");
var walk = require("voxel-walk");

var BLOCK_MAP = require("./blockmap.js").BLOCK_MAP;
var MATERIAL_MAP = require("./blockmap.js").MATERIAL_MAP;


TEXTURE_PATH = "./textures/";
SPEAKER_SKIN_PATH = TEXTURE_PATH + "speaker.png";
DEFAULT_BLOCK_ID = 66;
COORD_SHIFT = [5, -63, 5];
XMAX = 11;
YMAX = 9;
ZMAX = 11;

class Recorder {
  constructor() {
      this.coord_shift = [5, -63, 5];
      this.blocks = new Array(XMAX * YMAX * ZMAX).fill(0);
      this.pos = [0, 63, 0]
      this.pitch = 0;
      this.yaw = 0;
      this.timestamp = 0;
      this.tape = []
  }

  flattenIdx(index) {
      var x = parseInt(index / (YMAX * ZMAX));
      index = index % (YMAX * ZMAX);
      var y = parseInt(index / YMAX);
      index = index % YMAX;
      var z = index % ZMAX;
      return [x, y, z]
  }
  record_tick(blocks, pos, pitch, yaw) {
      var diff = [];
      var tape = {};
      for (var i = 0; i < self.blocks.length; i++) {
          if (this.blocks[i] != blocks[i]) {
              var xyz = this.flattenIdx(i);
              var x = xyz[0] - COORD_SHIFT[0];
              var y = xyz[1] - COORD_SHIFT[1];
              var z = xyz[2] - COORD_SHIFT[2];
              diff.push([x, y, z, this.blocks[i], blocks[i]]);
              this.blocks[i] = blocks[i];
          }
      }
      if (diff.length > 0) {
          var block_info = ""
          for (var i = 0; i < diff.length; ++i) {
              block_info += " (" + diff[i][0] + ", " + diff[i][1] + ", " + diff[i][2] + ", " + diff[i][3] + ", " + diff[i][4] + ")"
          }
          tape["block_change"] = block_info;
      }
      
      if (pos[0] != this.pos[0] || pos[1] != this.pos[1] || pos[2] != this.pos[2]) {
        tape["pos_change"] = "(" + pos[0] + ", " + pos[1] + ", " + pos[2] + ")"
        this.pos[0] = pos[0];
        this.pos[1] = pos[1];
        this.pos[2] = pos[2];
      }

      if (pitch != this.pitch || yaw != this.yaw) {
        tape["set_look"] = "(" + pitch + ", " + yaw + ")"
        this.pitch = pitch;
        this.yaw = yaw;
      }
      this.tape.push(tape);
      this.timestamp += 1;
  }
  record_action(action_name) {
      this.tape.push({"action": action_name});
      this.timestamp += 1;
  }

  stringify_tape() {
    var result = "";
    for(var i = 0; i < this.tape.length; ++i) {
      var tape_str = JSON.stringify(this.tape[i])
      if (tape_str != '{}') {
        for (const [key, value] of Object.entries(this.tape[i])) {
          result += i + " " + key + " " + value + "\n"
        }
      }
    }
    return result;
  }
}

function enableFly(game, target) {
  var makeFly = fly(game);
  game.flyer = makeFly(target);
}

function defaultSetup(game, avatar) {
  recorder = new Recorder();
  game.recorder = recorder;
  var makeFly = fly(game);
  var target = game.controls.target();
  game.flyer = makeFly(target);
  game.invs = [20, 20, 20, 20, 20, 20]
  // highlight blocks when you look at them, hold <Ctrl> for block placement
  var blockPosPlace, blockPosErase;
  var hl = (game.highlighter = highlight(game, { color: 0xff0000 }));
  hl.on("highlight", function (voxelPos) {
    blockPosErase = voxelPos;
  });
  hl.on("remove", function (voxelPos) {
    blockPosErase = null;
  });
  hl.on("highlight-adjacent", function (voxelPos) {
    blockPosPlace = voxelPos;
  });
  hl.on("remove-adjacent", function (voxelPos) {
    blockPosPlace = null;
  });

  // toggle between first and third person modes
  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "R".charCodeAt(0)) avatar.toggle();
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "1".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 57)
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "2".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 50)
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "3".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 59)
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "4".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 47)
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "5".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 56)
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "6".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 60)
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "W".charCodeAt(0)) {
      game.recorder.record_action("step_forward")
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "S".charCodeAt(0)) {
      game.recorder.record_action("step_backward")
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "A".charCodeAt(0)) {
      game.recorder.record_action("step_left")
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "D".charCodeAt(0)) {
      game.recorder.record_action("step_right")
    }
  });

  window.onbeforeunload = function () {
    var fileContent = game.recorder.stringify_tape();
    var bb = new Blob([fileContent ], { type: 'text/plain' });
    var a = document.createElement('a');
    a.download = 'download.txt';
    a.href = window.URL.createObjectURL(bb);
    a.click();
    return "Do you really want to close?";
  };

  // block interaction stuff, uses highlight data
  var currentMaterial = 1;

  game.on("fire", function (target, state) {
    var position = blockPosPlace;
    if (position) {
      game.createBlock(position, currentMaterial);
    } else {
      position = blockPosErase;
      if (position) game.setBlock(position, 0);
    }
  });

  game.on("tick", function () {
    blocks = new Array(XMAX * YMAX * ZMAX);
    for (ix = 0; ix < XMAX; ix ++) {
      for (iy = 0; iy < YMAX; iy++) {
        for (iz = 0; iz < ZMAX; iz++) {
          shifted_x = ix - COORD_SHIFT[0]
          shifted_y = iy - COORD_SHIFT[1]
          shifted_z = iz - COORD_SHIFT[2]
          block = game.getBlock(ix - COORD_SHIFT[0], iy - COORD_SHIFT[1], iz - COORD_SHIFT[2]);
          blocks[iz + iy * ZMAX + ix * YMAX * ZMAX] = block;
        }
      }
    }
    t = game.controls.target()
    p = parseFloat(t.pitch.rotation["x"])
    y = parseFloat(t.yaw.rotation["y"])
    pos = [parseFloat(t.position["x"]), parseFloat(t.position["y"]), parseFloat(t.position["z"])]
    game.recorder.record_tick(blocks, pos, p, y)

    walk.render(target.playerSkin);
    var vx = Math.abs(target.velocity.x);
    var vz = Math.abs(target.velocity.z);
    if (vx > 0.001 || vz > 0.001) walk.stopWalking();
    else walk.startWalking();
  });

  game.on('setBlock', function(pos, val, old) {
    console.log(pos)
    if (old == 0 && val != 0) {
      game.recorder.record_action("select_and_place_block " + val + " "+ pos[0] + " " + pos[1] + " " + pos[2])
    } else if (old != 0 && val == 0) {
      game.recorder.record_action("break "+ pos[0] + " " + pos[1] + " " + pos[2])
    }
  });
}

function World() {
  var vals = (function (opts, setup) {
    setup = setup || defaultSetup;
    var defaults = {
      generate: function (x, y, z) {
        if (x > 5 | x < -5 | z > 5 | z < -5) {
          return y < 63 ? 53 : 0;
        }
        return y < 63 ? 46 : 0;
      },
      chunkDistance: 2,
      materials: MATERIAL_MAP,
      worldOrigin: [0, 63, 0],
      controls: { discreteFire: true },
      texturePath: TEXTURE_PATH,
    };
    opts = extend({}, defaults, opts || {});

    // setup the game and add some trees
    var game = createGame(opts);
    var container = opts.container || document.body;
    window.game = game; // for debugging
    game.appendTo(container);
    if (game.notCapable()) return game;

    var createPlayer = player(game);

    // create the player from a minecraft skin file and tell the
    // game to use it as the main player
    var avatar = createPlayer(opts.playerSkin || SPEAKER_SKIN_PATH);
    avatar.possess();
    avatar.yaw.position.set(2, 14, 4);
    avatar.position.set(0, 63, 0);
    avatar.toggle();
    setup(game, avatar);
    return [avatar, game];
  })();
  this.speaker = vals[0];
  this.game = vals[1];

  this.avatars = {};
  this.avatars["player"] = this.speaker;
  this.game.control(this.speaker);

  /* private */
  this.getGame = function () {
    return this.game;
  };

  this.getAvatar = function (name) {
    return this.avatars[name];
  };

  this.setAgentLocation = function (name, x, y, z) {
    this.avatars[name].position.set(x, y, z);
  };

  /* public */
  this.updateAgents = function (agentsInfo) {
    for (var i = 0; i < agentsInfo.length; i++) {
      const name = agentsInfo[i]["name"];
      const x = agentsInfo[i]["x"];
      const y = agentsInfo[i]["y"];
      const z = agentsInfo[i]["z"];
      this.setAgentLocation(name, x, y, z);
    }
  };

  this.updateBlocks = function (blocksInfo) {
    for (var i = 0; i < blocksInfo.length; i++) {
      let [xyz, idm] = blocksInfo[i];
      var id = BLOCK_MAP[idm.toString()];
      if (id == undefined) {
        id = DEFAULT_BLOCK_ID;
      }
      if (id == 0) {
        this.game.setBlock(xyz, id);
      } else {
        this.game.createBlock(xyz, id);
      }
    }
  };

  this.setBlock = function (x, y, z, idm) {
    this.game.setBlock([x, y, z], idm);
  };
}

module.exports = World;
