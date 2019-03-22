$(document).ready(function () {

    $('.sidebar li.menu-collapse > a').click(function () {
        console.log('clicked');
        $(this).parent().toggleClass('expanded');
    });

});