$(document).ready(function () {

    $('.wy-menu-vertical li.menu-collapse > a').click(function () {
        console.log('clicked');
        $(this).parent().toggleClass('expanded');
    });

});