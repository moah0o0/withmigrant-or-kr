/**
 * 양산외국인노동자의집 메인 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    initMobileMenu();

    // Activity Cards Interaction
    initActivityCards();

    // Smooth Scroll for Anchor Links
    initSmoothScroll();

    // Navigation Scroll Effect
    initNavScroll();
});

/**
 * 모바일 메뉴 초기화
 */
function initMobileMenu() {
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    const menuIcon = menuToggle?.querySelector('.menu-icon');
    const closeIcon = menuToggle?.querySelector('.close-icon');

    if (menuToggle && mobileMenu) {
        menuToggle.addEventListener('click', function() {
            const isOpen = !mobileMenu.classList.contains('hidden');

            if (isOpen) {
                mobileMenu.classList.add('hidden');
                menuIcon?.classList.remove('hidden');
                closeIcon?.classList.add('hidden');
            } else {
                mobileMenu.classList.remove('hidden');
                menuIcon?.classList.add('hidden');
                closeIcon?.classList.remove('hidden');
            }
        });
    }

    // Mobile Dropdown
    const mobileDropdownTriggers = document.querySelectorAll('.mobile-dropdown-trigger');
    mobileDropdownTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const dropdown = this.nextElementSibling;
            const arrow = this.querySelector('.dropdown-arrow');

            if (dropdown) {
                dropdown.classList.toggle('hidden');
                arrow?.classList.toggle('rotate-180');
            }
        });
    });

    // Hero Mobile Menu Toggle
    const heroMenuToggle = document.getElementById('hero-mobile-menu-toggle');
    if (heroMenuToggle && mobileMenu) {
        heroMenuToggle.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

/**
 * 활동 카드 인터랙션 초기화
 */
function initActivityCards() {
    const activityCards = document.querySelectorAll('.activity-card');

    activityCards.forEach(card => {
        // 클릭 시 active 상태 토글
        card.addEventListener('click', function() {
            // 다른 카드의 active 상태 제거
            activityCards.forEach(c => {
                if (c !== this) {
                    c.classList.remove('active');
                }
            });

            // 현재 카드 토글
            this.classList.toggle('active');
        });
    });

    // Activities Pagination
    const activitiesGrid = document.getElementById('activities-grid');
    const prevBtn = document.getElementById('activities-prev');
    const nextBtn = document.getElementById('activities-next');

    if (activitiesGrid && prevBtn && nextBtn) {
        const cards = activitiesGrid.querySelectorAll('.activity-card');
        const totalCards = cards.length;
        const cardsPerPage = window.innerWidth >= 768 ? 3 : 1;
        const totalPages = Math.ceil(totalCards / cardsPerPage);
        let currentPage = 0;

        function updatePagination() {
            const counter = document.querySelector('.activities-pagination .pagination-counter');
            if (counter) {
                counter.textContent = `${currentPage + 1}/${totalPages}`;
            }

            // Hide/show cards based on current page
            cards.forEach((card, index) => {
                const startIndex = currentPage * cardsPerPage;
                const endIndex = startIndex + cardsPerPage;

                if (window.innerWidth >= 768) {
                    if (index >= startIndex && index < endIndex) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                } else {
                    // Mobile: show only one card
                    if (index === currentPage) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        }

        prevBtn.addEventListener('click', function() {
            if (window.innerWidth >= 768) {
                currentPage = (currentPage - 1 + totalPages) % totalPages;
            } else {
                currentPage = (currentPage - 1 + totalCards) % totalCards;
            }
            updatePagination();
        });

        nextBtn.addEventListener('click', function() {
            if (window.innerWidth >= 768) {
                currentPage = (currentPage + 1) % totalPages;
            } else {
                currentPage = (currentPage + 1) % totalCards;
            }
            updatePagination();
        });

        // Initial update
        updatePagination();

        // Update on resize
        window.addEventListener('resize', function() {
            currentPage = 0;
            updatePagination();
        });
    }
}

/**
 * 부드러운 스크롤 초기화
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');

            if (href && href !== '#') {
                const target = document.querySelector(href);

                if (target) {
                    e.preventDefault();

                    const navHeight = document.querySelector('.nav-container')?.offsetHeight || 80;
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });

                    // Close mobile menu if open
                    const mobileMenu = document.getElementById('mobile-menu');
                    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                        mobileMenu.classList.add('hidden');
                    }
                }
            }
        });
    });
}

/**
 * 네비게이션 스크롤 효과 초기화
 */
function initNavScroll() {
    const nav = document.querySelector('.nav-container');
    const heroSection = document.querySelector('.hero-section');

    if (nav && !heroSection) {
        // 히어로 섹션이 없는 페이지에서는 항상 보이게
        nav.style.background = 'white';
    }

    window.addEventListener('scroll', function() {
        const scrollY = window.scrollY;

        if (nav) {
            if (scrollY > 100) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        }
    });
}

/**
 * 이미지 지연 로딩
 */
function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');

    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    }
}
