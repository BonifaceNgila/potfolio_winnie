const menuButton = document.querySelector('.menu-toggle');
const navLinks = document.querySelector('.nav-links');
const year = document.getElementById('year');

if (year) {
  year.textContent = new Date().getFullYear();
}

const getHeaderOffset = () => {
  const header = document.querySelector('.site-header');
  return header ? header.getBoundingClientRect().height + 12 : 0;
};

const scrollToTarget = (target) => {
  const top = target.getBoundingClientRect().top + window.scrollY - getHeaderOffset();
  window.scrollTo({ top: Math.max(top, 0), behavior: 'smooth' });
};

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener('click', (event) => {
    const hash = link.getAttribute('href');

    if (!hash || hash === '#') {
      return;
    }

    const target = hash === '#top' ? document.body : document.querySelector(hash);

    if (!target) {
      return;
    }

    event.preventDefault();
    scrollToTarget(target);
    history.pushState(null, '', hash);

    if (menuButton && navLinks) {
      navLinks.classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
    }
  });
});

if (menuButton && navLinks) {
  menuButton.addEventListener('click', () => {
    const isOpen = navLinks.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(isOpen));
  });
}

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1 }
);

document.querySelectorAll('.reveal').forEach((item) => observer.observe(item));
