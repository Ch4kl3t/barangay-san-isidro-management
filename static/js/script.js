document.addEventListener('DOMContentLoaded', () => {

    // --- SIDEBAR TOGGLE LOGIC ---
    const burgerBtn = document.getElementById('burger-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    function toggleSidebar() {
        if (sidebar) sidebar.classList.toggle('open');
        if (document.body) document.body.classList.toggle('sidebar-open');
    }

    if (burgerBtn) burgerBtn.addEventListener('click', toggleSidebar);
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            document.body.classList.remove('sidebar-open');
        });
    }

    // --- SIDEBAR DROPDOWN LOGIC ---
    const dropdownItems = document.querySelectorAll('.sidebar .dropdown > a');
    dropdownItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const parent = item.parentElement;
            const submenu = parent.querySelector('.submenu');
            if (submenu) {
                e.preventDefault();
                parent.classList.toggle('active');
                submenu.style.maxHeight = parent.classList.contains('active') ? submenu.scrollHeight + "px" : "0";
            }
        });
    });

    // --- UNIVERSAL SEARCH LOGIC ---
    const searchInput = document.getElementById("searchBox") || document.getElementById("member-search");
    const suggestionsPanel = document.getElementById("suggestions") || document.getElementById("member-suggestions");

    if (searchInput && suggestionsPanel) {
        searchInput.addEventListener("input", async function () {
            const query = this.value.trim();
            const householdRows = document.querySelectorAll('.household-row');
            const residentRows = document.querySelectorAll('.resident-row');

            // 1. Reset everything if query is empty
            if (query.length === 0) {
                [...householdRows, ...residentRows].forEach(row => row.style.display = '');
                suggestionsPanel.style.display = "none";
                return;
            }

            try {
                let endpoint;
                // 2. Decide which endpoint to use based on the page you are on
                if (householdRows.length > 0) {
                    endpoint = `/search_households?q=${encodeURIComponent(query)}`;
                } else if (residentRows.length > 0) {
                    endpoint = `/search_members?q=${encodeURIComponent(query)}`;
                } else {
                    // If no rows found, we are likely on the Dashboard
                    endpoint = `/search_members?q=${encodeURIComponent(query)}`; 
                }

                let res = await fetch(endpoint);
                let data = await res.json();

                suggestionsPanel.innerHTML = "";
                if (!data || data.length === 0) {
                    suggestionsPanel.innerHTML = '<div style="padding: 15px; color: #666;">No results found.</div>';
                    suggestionsPanel.style.display = "block";
                    return;
                }

                suggestionsPanel.style.display = "block";

                data.forEach(item => {
                    // Match Python keys: 'name', 'subtext', 'type', 'id'
                    const div = document.createElement("div");
                    div.className = "search-item";
                    div.style.padding = "10px 15px";
                    div.style.cursor = "pointer";
                    div.style.borderBottom = "1px solid #eee";

                    const tagColor = item.type === 'resident' ? '#e0f2fe' : '#dcfce7';
                    const textColor = item.type === 'resident' ? '#0369a1' : '#166534';

                    div.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: bold; color: #1B3A57;">${highlight(item.name, query)}</div>
                                <div style="font-size: 12px; color: #666;">${item.subtext}</div>
                            </div>
                            <span style="background: ${tagColor}; color: ${textColor}; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">
                                ${item.type.toUpperCase()}
                            </span>
                        </div>
                    `;

                    div.onclick = () => {
                        // If we are on the Dashboard (no rows present), Redirect
                        if (householdRows.length === 0 && residentRows.length === 0) {
                            window.location.href = item.type === 'resident' ? `/edit_member/${item.id}` : `/view_household/${item.id}`;
                        } else {
                            // If we are on a list page, filter the table
                            searchInput.value = item.name;
                            suggestionsPanel.style.display = "none";
                            
                            const targetRows = householdRows.length > 0 ? householdRows : residentRows;
                            targetRows.forEach(row => {
                                const text = row.innerText.toLowerCase();
                                row.style.display = text.includes(item.name.toLowerCase()) ? '' : 'none';
                            });
                        }
                    };
                    suggestionsPanel.appendChild(div);
                });

            } catch (err) {
                console.error("Search error:", err);
            }
        });

        // Close suggestions when clicking outside
        document.addEventListener("click", (e) => {
            if (!searchInput.contains(e.target) && !suggestionsPanel.contains(e.target)) {
                suggestionsPanel.style.display = "none";
            }
        });
    }

    function highlight(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, "gi");
        return text.replace(regex, "<mark style='background: #ffd700; color: black;'>$1</mark>");
    }
});