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

// const { BlobServiceClient } = require('@azure/storage-blob');
var azure = require("azure-storage");

var html2canvas = require("html2canvas");

// TEXTURE_PATH = "./textures/";
TEXTURE_PATH = "https://cdn.jsdelivr.net/gh/snyxan/myWorld@main/textures/";
SPEAKER_SKIN_PATH = TEXTURE_PATH + "agent.png";
DEFAULT_BLOCK_ID = 66;
LETTER_R_ID = 67;
COORD_SHIFT = [5, -63, 5];
XMAX = 11;
YMAX = 9;
ZMAX = 11;
COMPASS_MARK_N = [
  [-2, 62, -9],
  [-2, 62, -10],
  [-2, 62, -11],
  [-2, 62, -12],
  [-2, 62, -13],
  [-1, 62, -12],
  [0, 62, -11],
  [1, 62, -10],
  [2, 62, -9],
  [2, 62, -10],
  [2, 62, -11],
  [2, 62, -12],
  [2, 62, -13],
];
COMPASS_MARK_W = [
  [-10, 62, 0],
  [-11, 62, 0],
  [-9, 62, 1],
  [-10, 62, 1],
  [-10, 62, 2],
  [-11, 62, 2],
  [-12, 62, 2],
  [-12, 62, 3],
  [-13, 62, 3],
  [-9, 62, -1],
  [-10, 62, -1],
  [-10, 62, -2],
  [-11, 62, -2],
  [-12, 62, -2],
  [-12, 62, -3],
  [-13, 62, -3],
];
COMPASS_MARK_E = [
  [9, 62, -1],
  [10, 62, -1],
  [11, 62, -1],
  [12, 62, -1],
  [13, 62, -1],
  [9, 62, 0],
  [11, 62, 0],
  [13, 62, 0],
  [9, 62, 1],
  [11, 62, 1],
  [13, 62, 1],
];
COMPASS_MARK_S = [
  [1, 62, 9],
  [1, 62, 12],
  [0, 62, 9],
  [0, 62, 11],
  [0, 62, 13],
  [-1, 62, 9],
  [-1, 62, 11],
  [-1, 62, 13],
  [-2, 62, 10],
  [-2, 62, 13],
];

class Recorder {
  constructor() {
    this.coord_shift = [5, -63, 5];
    this.blocks = new Array(XMAX * YMAX * ZMAX).fill(0);
    this.pos = [0, 63, 0];
    this.pitch = 0;
    this.yaw = 0;
    this.timestamp = 0;
    this.tape = [];
    this.world_just_recovered = false;
  }

  flattenIdx(index) {
    var x = parseInt(index / (YMAX * ZMAX));
    index = index % (YMAX * ZMAX);
    var y = parseInt(index / ZMAX);
    index = index % ZMAX;
    var z = index % ZMAX;
    return [x, y, z];
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
      var block_info = "";
      for (var i = 0; i < diff.length; ++i) {
        block_info +=
          " (" +
          diff[i][0] +
          ", " +
          diff[i][1] +
          ", " +
          diff[i][2] +
          ", " +
          diff[i][3] +
          ", " +
          diff[i][4] +
          ")";
      }
      tape["block_change"] = block_info;
    }

    if (
      pos[0] != this.pos[0] ||
      pos[1] != this.pos[1] ||
      pos[2] != this.pos[2]
    ) {
      tape["pos_change"] = "(" + pos[0] + ", " + pos[1] + ", " + pos[2] + ")";
      this.pos[0] = pos[0];
      this.pos[1] = pos[1];
      this.pos[2] = pos[2];
    }

    if (pitch != this.pitch || yaw != this.yaw) {
      tape["set_look"] = "(" + pitch + ", " + yaw + ")";
      this.pitch = pitch;
      this.yaw = yaw;
    }
    this.tape.push(tape);
    this.timestamp += 1;

    if (this.world_just_recovered == true) {
      game.recorder.record_action("finish_recover_world_state");
      this.world_just_recovered = false;
    }
  }
  record_action(action_name) {
    this.tape.push({ action: action_name });
    this.timestamp += 1;
  }

  stringify_tape() {
    var result = "";
    for (var i = 0; i < this.tape.length; ++i) {
      var tape_str = JSON.stringify(this.tape[i]);
      if (tape_str != "{}") {
        for (const [key, value] of Object.entries(this.tape[i])) {
          result += i + " " + key + " " + value + "\n";
        }
      }
    }
    return result;
  }
}

function uploadToAzure(
  game,
  blobService,
  containerName,
  blobName,
  blobContent,
  callback
) {
  document.querySelector("canvas").click();

  blobService.createBlockBlobFromText(
    containerName,
    blobName,
    blobContent,
    null,
    function (error) {
      console.log(error);
    }
  );

  // set agent to face down
  var avatar = game.controls.target();
  avatar.position["x"] = 0;
  avatar.position["y"] = 85;
  avatar.position["z"] = 8;
  avatar.pitch.rotation["x"] = -1.5;
  avatar.yaw.rotation["y"] = -6.28;

  var top_screenshot = undefined;
  var north_screenshot = undefined;
  var south_screenshot = undefined;
  var west_screenshot = undefined;
  var east_screenshot = undefined;

  setTimeout(function () {
    var canvas = document.querySelector("canvas");
    var rawdata = canvas.toDataURL();
    var matches = rawdata.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
    top_screenshot = new Buffer(matches[2], "base64");

    // set agent to face north
    var avatar = game.controls.target();
    avatar.position["x"] = 0;
    avatar.position["y"] = 68;
    avatar.position["z"] = 10.5;
    avatar.pitch.rotation["x"] = -0.8;
    avatar.yaw.rotation["y"] = 0;
  }, 100);

  setTimeout(function () {
    var canvas = document.querySelector("canvas");
    var rawdata = canvas.toDataURL();
    var matches = rawdata.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
    north_screenshot = new Buffer(matches[2], "base64");

    // set agent to face south
    var avatar = game.controls.target();
    avatar.position["x"] = 0;
    avatar.position["y"] = 68;
    avatar.position["z"] = -10.5;
    avatar.pitch.rotation["x"] = -0.8;
    avatar.yaw.rotation["y"] = -3.15;
  }, 200);

  setTimeout(function () {
    var canvas = document.querySelector("canvas");
    var rawdata = canvas.toDataURL();
    var matches = rawdata.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
    south_screenshot = new Buffer(matches[2], "base64");

    // set agent to face east
    var avatar = game.controls.target();
    avatar.position["x"] = -10.5;
    avatar.position["y"] = 68;
    avatar.position["z"] = 0;
    avatar.pitch.rotation["x"] = -0.8;
    avatar.yaw.rotation["y"] = -1.57;
  }, 300);

  setTimeout(function () {
    var canvas = document.querySelector("canvas");
    var rawdata = canvas.toDataURL();
    var matches = rawdata.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
    east_screenshot = new Buffer(matches[2], "base64");

    // set agent to face west
    var avatar = game.controls.target();
    avatar.position["x"] = 10.5;
    avatar.position["y"] = 68;
    avatar.position["z"] = 0;
    avatar.pitch.rotation["x"] = -0.8;
    avatar.yaw.rotation["y"] = -4.7;
  }, 400);

  setTimeout(function () {
    var canvas = document.querySelector("canvas");
    var rawdata = canvas.toDataURL();
    var matches = rawdata.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
    west_screenshot = new Buffer(matches[2], "base64");
    console.log(top_screenshot);
    console.log(west_screenshot);
    console.log(east_screenshot);
    console.log(north_screenshot);
    console.log(south_screenshot);

    blobService.createBlockBlobFromText(
      containerName,
      blobName + "_top.png",
      top_screenshot,
      { contentSettings: { contentType: "image/png" } },
      function (error) {
        console.log(error);
      }
    );
    blobService.createBlockBlobFromText(
      containerName,
      blobName + "_north.png",
      north_screenshot,
      { contentSettings: { contentType: "image/png" } },
      function (error) {
        console.log(error);
      }
    );
    blobService.createBlockBlobFromText(
      containerName,
      blobName + "_south.png",
      south_screenshot,
      { contentSettings: { contentType: "image/png" } },
      function (error) {
        console.log(error);
      }
    );
    blobService.createBlockBlobFromText(
      containerName,
      blobName + "_west.png",
      west_screenshot,
      { contentSettings: { contentType: "image/png" } },
      function (error) {
        console.log(error);
      }
    );
    blobService.createBlockBlobFromText(
      containerName,
      blobName + "_east.png",
      east_screenshot,
      { contentSettings: { contentType: "image/png" } },
      function (error) {
        console.log(error);
        callback();
      }
    );
  }, 500);
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
  game.flyer.startFlying();

  game.invs = [20, 20, 20, 20, 20, 20];
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
  // window.addEventListener("keydown", function (ev) {
  //   if (ev.keyCode === "R".charCodeAt(0)) avatar.toggle();
  // });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "1".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 86);
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "2".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 87);
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "3".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 88);
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "4".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 89);
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "5".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 90);
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "6".charCodeAt(0)) {
      game.createAdjacent(game.raycastVoxels(), 91);
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "W".charCodeAt(0)) {
      game.recorder.record_action("step_forward");
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "S".charCodeAt(0)) {
      game.recorder.record_action("step_backward");
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "A".charCodeAt(0)) {
      game.recorder.record_action("step_left");
    }
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.keyCode === "D".charCodeAt(0)) {
      game.recorder.record_action("step_right");
    }
  });

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
    for (ix = 0; ix < XMAX; ix++) {
      for (iy = 0; iy < YMAX; iy++) {
        for (iz = 0; iz < ZMAX; iz++) {
          shifted_x = ix - COORD_SHIFT[0];
          shifted_y = iy - COORD_SHIFT[1];
          shifted_z = iz - COORD_SHIFT[2];
          block = game.getBlock(
            ix - COORD_SHIFT[0],
            iy - COORD_SHIFT[1],
            iz - COORD_SHIFT[2]
          );
          blocks[iz + iy * ZMAX + ix * YMAX * ZMAX] = block;
        }
      }
    }
    t = game.controls.target();
    p = parseFloat(t.pitch.rotation["x"]);
    y = parseFloat(t.yaw.rotation["y"]);
    pos = [
      parseFloat(t.position["x"]),
      parseFloat(t.position["y"]),
      parseFloat(t.position["z"]),
    ];
    game.recorder.record_tick(blocks, pos, p, y);

    walk.render(target.playerSkin);
    var vx = Math.abs(target.velocity.x);
    var vz = Math.abs(target.velocity.z);
    if (vx > 0.001 || vz > 0.001) walk.stopWalking();
    else walk.startWalking();
  });

  game.on("setBlock", function (pos, val, old) {
    const cameraPos = game.cameraPosition();
    const cameraVec = game.cameraVector();
    if (old == 0 && val != 0) {
      game.recorder.record_action(
        "select_and_place_block " +
          val +
          " " +
          pos[0] +
          " " +
          pos[1] +
          " " +
          pos[2] +
          " " +
          cameraPos[0] + 
          " " +
          cameraPos[1] + 
          " " +
          cameraPos[2] + 
          " " +
          cameraVec[0] + 
          " " +
          cameraVec[1] + 
          " " +
          cameraVec[2]
      );
    } else if (old != 0 && val == 0) {
      game.recorder.record_action(
        "break " + 
          pos[0] + 
          " " + 
          pos[1] + 
          " " + 
          pos[2] +
          " " +
          cameraPos[0] + 
          " " +
          cameraPos[1] + 
          " " +
          cameraPos[2] + 
          " " +
          cameraVec[0] + 
          " " +
          cameraVec[1] + 
          " " +
          cameraVec[2]
      );
    }
  });
}

function World() {
  var vals = (function (opts, setup) {
    setup = setup || defaultSetup;
    var defaults = {
      generate: function (x, y, z) {
        if ((x > 5) | (x < -5) | (z > 5) | (z < -5)) {
          return y < 63 ? 53 : 0;
        }
        if ((x + z) % 2 == 0) {
          return y < 63 ? 46 : 0;
        } else {
          return y < 63 ? 54 : 0;
        }
        // return y < 63 ? 46 : 0;
      },
      chunkDistance: 2,
      materials: MATERIAL_MAP,
      worldOrigin: [0, 63, 0],
      controls: { discreteFire: true },
      texturePath: TEXTURE_PATH,
    };
    opts = extend({}, defaults, opts || {});
    opts.container = document.getElementById("worlddiv");
    opts.statsDisabled = true;
    // setup the game and add some trees
    var game = createGame(opts);
    var container = opts.container || document.body;
    window.game = game; // for debugging

    container = document.getElementById("worlddiv");

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

  // for (var i = 0; i < COMPASS_MARK_N.length; i++) {
  //   var xyz = COMPASS_MARK_N[i]
  //   this.game.setBlock([xyz[0], xyz[1], xyz[2]], 61, true)
  // }

  // for (var i = 0; i < COMPASS_MARK_W.length; i++) {
  //   var xyz = COMPASS_MARK_W[i]
  //   this.game.setBlock([xyz[0], xyz[1], xyz[2]], 61, true)
  // }

  // for (var i = 0; i < COMPASS_MARK_E.length; i++) {
  //   var xyz = COMPASS_MARK_E[i]
  //   this.game.setBlock([xyz[0], xyz[1], xyz[2]], 61, true)
  // }

  // for (var i = 0; i < COMPASS_MARK_S.length; i++) {
  //   var xyz = COMPASS_MARK_S[i]
  //   this.game.setBlock([xyz[0], xyz[1], xyz[2]], 61, true)
  // }

  // Show compass on the ground, TODO: civilize it
  this.game.setBlock([-2, 62, -9], 68, true);
  this.game.setBlock([-1, 62, -9], 69, true);
  this.game.setBlock([0, 62, -9], 70, true);
  this.game.setBlock([1, 62, -9], 71, true);
  this.game.setBlock([2, 62, -9], 72, true);

  this.game.setBlock([2, 62, 9], 73, true);
  this.game.setBlock([1, 62, 9], 74, true);
  this.game.setBlock([0, 62, 9], 75, true);
  this.game.setBlock([-1, 62, 9], 76, true);
  this.game.setBlock([-2, 62, 9], 77, true);

  this.game.setBlock([9, 62, -2], 78, true);
  this.game.setBlock([9, 62, -1], 79, true);
  this.game.setBlock([9, 62, 0], 80, true);
  this.game.setBlock([9, 62, 1], 81, true);

  this.game.setBlock([-9, 62, 1], 82, true);
  this.game.setBlock([-9, 62, 0], 83, true);
  this.game.setBlock([-9, 62, -1], 84, true);
  this.game.setBlock([-9, 62, -2], 85, true);

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

  this.recoverWorldState = function (
    blobServiceName,
    sas,
    containerName,
    blobName
  ) {
    var blobService = azure.createBlobServiceWithSas(blobServiceName, sas);
    blobService.getBlobToText(
      containerName,
      blobName,
      null,
      function (error, text, blockBlob, response) {
        game.recorder.record_action("start_recover_world_state");
        const data = JSON.parse(text);
        const worldState = data["worldEndingState"];
        for (const blockInfo of worldState["blocks"]) {
          game.setBlock(
            [blockInfo[0], blockInfo[1], blockInfo[2]],
            blockInfo[3]
          );
        }

        const avatarInfo = data["avatarInfo"];
        const avatarPos = avatarInfo["pos"];
        const avatarLook = avatarInfo["look"];
        var avatar = game.controls.target();
        avatar.position["x"] = avatarPos[0];
        avatar.position["y"] = avatarPos[1];
        avatar.position["z"] = avatarPos[2];
        avatar.pitch.rotation["x"] = avatarLook[0];
        avatar.yaw.rotation["y"] = avatarLook[1];

        game.recorder.world_just_recovered = true;
      }
    );

    var canvas = document.querySelector("canvas");
    fitToContainer(canvas);

    function fitToContainer(canvas) {
      // Make it visually fill the positioned parent
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      // ...then set the internal size to match
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    }
  };

  this.uploadToCloud = function (
    blobServiceName,
    sas,
    containerName,
    blobName,
    callback
  ) {
    var tape = this.game.recorder.stringify_tape();
    var avatar = game.controls.target();
    var data = {
      gameId: 19,
      stepId: 1,
      avatarInfo: {
        pos: [avatar.position["x"], avatar.position["y"], avatar.position["z"]],
        look: [avatar.pitch.rotation["x"], avatar.yaw.rotation["y"]],
      },
      worldEndingState: {
        blocks: [],
      },
      tape: tape, // use string instead of array here for now
      clarification_question: "null",
    };

    for (ix = 0; ix < XMAX; ix++) {
      for (iy = 0; iy < YMAX; iy++) {
        for (iz = 0; iz < ZMAX; iz++) {
          shifted_x = ix - COORD_SHIFT[0];
          shifted_y = iy - COORD_SHIFT[1];
          shifted_z = iz - COORD_SHIFT[2];
          block = game.getBlock(shifted_x, shifted_y, shifted_z);
          if (block != 0) {
            data["worldEndingState"]["blocks"].push([
              shifted_x,
              shifted_y,
              shifted_z,
              block,
            ]);
          }
        }
      }
    }
    // console.log(data)

    var blobService = azure.createBlobServiceWithSas(blobServiceName, sas);
    fileContent = JSON.stringify(data);
    uploadToAzure(
      game,
      blobService,
      containerName,
      blobName,
      fileContent,
      callback
    );
  };
}

module.exports = World;
