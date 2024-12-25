const open_menu_button = document.querySelector('.menu');
const menu_wrapper = document.querySelector('.menu_wrapper');
const close_menu_button = document.querySelector('.close_menu');
const menu_a = document.querySelectorAll('.menu-a');

open_menu_button.addEventListener('click', () => {
  menu_wrapper.style.display = 'flex';
});

close_menu_button.addEventListener('click', () => {
  menu_wrapper.style.display = 'none';
});

menu_a.forEach((menu_a) => {
  menu_a.addEventListener('click', () => {
    menu_wrapper.style.display = 'none';
  });
});

document.querySelectorAll('a[href^="#"]').forEach((anchorElement) => {
  anchorElement.addEventListener('click', function (e) {
    e.preventDefault();

    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth',
    });
  });
});
