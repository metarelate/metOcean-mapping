$(document).ready(function(){

    var ref;
    $('#search').val('');

    $("#search").keyup(function(e){
        window.clearTimeout(ref);
        $('#search').css('background','palegreen');
        $('#action').show()
        ref = window.setTimeout(search, 300);
    })

    function search(){
        ref = null;
        var searchstr = $('#search').val();
        if( searchstr == '' ){
            $("div.format").show();
        }else{
            console.time('foo');
            $('div.urllabel').each(function(){
                var uri = $(this).text();
                if( uri.indexOf(searchstr) == -1 ){
                    $(this).parent().parent().hide();
                }else{
                    $(this).parent().parent().show();
                } 
            });                                                                                            
        }                                                                                                  
        console.timeEnd('foo');                                                                            
        $('#action').hide()                                                                                
        $('#search').css('background','');                                                                 
    }                                                                                                      
                                                                                                           
    var ac = $('#id_metadata_element').autocomplete({                                                      
        lookup: [{{ prefix_lookup }}],                                                                     
        width: 600,                                                                                        
    })                                                                                                     
                                                                                                           
})                                                                                                         

