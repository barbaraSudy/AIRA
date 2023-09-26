const GPTResearcher = (() => {
    const startResearch = () => {
      document.getElementById("output").innerHTML = "";
      listenToSockEvents();
    };
  
    const listenToSockEvents = () => {
      const { protocol, host, pathname } = window.location;
      const ws_uri = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${host}${pathname}ws`;
      const socket = new WebSocket(ws_uri);
  
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'logs') {
          addResponse(data);
        } 
      };
  
      socket.onopen = (event) => {
        const task = document.querySelector('input[name="task"]').value;
  
        const requestData = {
          task: task
        };
  
        socket.send(`start ${JSON.stringify(requestData)}`);
      };
    };
  
    const addResponse = (data) => {
      const output = document.getElementById("output");
      output.innerHTML += '<div class="response">' + data.output + '</div>';
    };
  
    return {
      startResearch,
    };
  })();
