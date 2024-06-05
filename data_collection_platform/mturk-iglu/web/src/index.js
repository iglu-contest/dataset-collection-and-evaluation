/*
Copyright (c) Facebook, Inc. and its affiliates.
*/
import React from "react";
import ReactDOM from "react-dom";

import GoldenLayout from "golden-layout";
import "golden-layout/src/css/goldenlayout-base.css";
import "golden-layout/src/css/goldenlayout-dark-theme.css";

import VoxelWorld from "./components/VoxelWorld/VoxelWorld";

import "./index.css";

window.React = React;
window.ReactDOM = ReactDOM;

var config = {
  settings: {
    showPopoutIcon: false,
  },
  content: [
    {
      type: "row",
      content: [
        {
          type: "stack",
          content: [
            {
              title: "Voxel World",
              type: "react-component",
              component: "VoxelWorld",
            },
          ],
        },
      ],
    },
  ],
};

var dashboardLayout = new GoldenLayout(config);
dashboardLayout.registerComponent("VoxelWorld", VoxelWorld);
dashboardLayout.init();

