myFunction = function(e) {
  // prevents default action to happen
  e.preventDefault();
  // Get the content of the PDGA Number field
  pdga_number = document.getElementById("pdganumber").value
  console.log(pdga_number)

  // If is passes the check we add the email to the database
  endpoint = "https://www.pdga.com/player/" + pdga_number + "/details"

  var xhr = new XMLHttpRequest();
  xhr.open("GET", endpoint)

  xhr.onload = function(){
      console.log(this)
      }
  xhr.send();
  }