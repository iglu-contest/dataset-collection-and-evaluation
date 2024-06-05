import React from "react";

class VoxelWorld extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      status: "",
    };
    this.worldContainerRef = React.createRef();
    this.uploadToCloud = this.uploadToCloud.bind(this);
  }

  uploadToCloud() {
    this.worldContainerRef.current.contentWindow.postMessage(
      "uploadToCloud",
      "*"
    );
  }

  render() {
    return (
      <div id="world-container">
        <iframe
          id="ifr"
          src="VoxelWorld/world.html"
          title="Voxel World"
          width="1000"
          height="600"
          ref={this.worldContainerRef}
        ></iframe>
        <button onClick={this.uploadToCloud}>uploadToCloud</button>
      </div>
    );
  }
}

export default VoxelWorld;
