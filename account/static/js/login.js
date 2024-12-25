const password = document.getElementById("password"),
    eye = document.getElementById("eye");


eye.addEventListener("click", () => {
    if ( password.type === "password" ){
        password.setAttribute("type", "text")
    }else {
        password.setAttribute("type", "password")
    }
})