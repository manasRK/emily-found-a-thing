function register(){
    var target=document.getElementById("target");
    var request=new XMLHttpRequest();
    var formValue=document.getElementById("submissionForm").elements[0].value;
    request.onreadystatechange=function(){
        if (request.readyState==4 && request.status==200){
            target.innerHTML=request.responseText;
        }
    };
    if(formValue!==""){
        request.open("GET","http://emily.appspot.com/add?url="+encodeURI(formValue),true);
        request.send();
    }
}