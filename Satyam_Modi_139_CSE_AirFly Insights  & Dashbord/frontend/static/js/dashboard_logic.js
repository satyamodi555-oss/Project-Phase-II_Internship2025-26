// Dashboard Logic - Simplified for Power BI Integration
// This file now only handles the Action Hub, FAQ, and Country Comparison sections.

// Initialization function
async function initDashboard() {
    try {
        console.log("Fetching comparison data...");
        const response = await fetch('/api/dashboard-data');
        const data = await response.json();

        // --- Country Comparison Logic ---
        
        // Populate comparison selectors
        const compYear1 = document.getElementById('compYear1');
        const compYear2 = document.getElementById('compYear2');
        const compC1 = document.getElementById('compCountry1');
        const compC2 = document.getElementById('compCountry2');
        
        if (compYear1 && compYear2 && compC1 && compC2) {
            data.years.forEach(y => {
                compYear1.add(new Option(y, y));
                compYear2.add(new Option(y, y));
            });
            
            data.countries.forEach(c => {
                compC1.add(new Option(c, c));
                compC2.add(new Option(c, c));
            });
        }

        const btnCompare = document.getElementById('btnCompare');
        if (btnCompare) {
            btnCompare.addEventListener('click', async () => {
                const country1 = compC1.value;
                const country2 = compC2.value;
                const year1 = compYear1.value;
                const year2 = compYear2.value;

                if (!country1 || !country2 || !year1 || !year2) {
                    alert("Please select both countries and their respective years to compare.");
                    return;
                }

                // Show loader, hide result
                document.getElementById('compResult').style.display = 'none';
                document.getElementById('compLoader').style.display = 'block';

                try {
                    const url = `/api/country-comparison?country1=${encodeURIComponent(country1)}&country2=${encodeURIComponent(country2)}&year1=${year1}&year2=${year2}`;
                    const response = await fetch(url);
                    const result = await response.json();

                    if (!response.ok) {
                        throw new Error(result.error || "Failed to fetch comparison data.");
                    }

                    renderComparison(result);
                    document.getElementById('compLoader').style.display = 'none';
                    document.getElementById('compResult').style.display = 'block';
                    
                    if (typeof AOS !== 'undefined') AOS.refresh();

                    document.getElementById('compResult').scrollIntoView({ behavior: 'smooth', block: 'start' });

                } catch (error) {
                    document.getElementById('compLoader').style.display = 'none';
                    alert("Error: " + error.message);
                }
            });
        }

        // Swap functionality
        const btnSwap = document.getElementById('btnSwap');
        if (btnSwap) {
            btnSwap.addEventListener('click', () => {
                const tempC = compC1.value;
                compC1.value = compC2.value;
                compC2.value = tempC;

                const tempY = compYear1.value;
                compYear1.value = compYear2.value;
                compYear2.value = tempY;
                
                if (document.getElementById('compResult').style.display === 'block') {
                    document.getElementById('btnCompare').click();
                }
            });
        }

        // Clear functionality
        const btnClearComp = document.getElementById('btnClearComp');
        if (btnClearComp) {
            btnClearComp.addEventListener('click', () => {
                document.getElementById('compResult').style.display = 'none';
                compC1.value = "";
                compC2.value = "";
                compYear1.value = "";
                compYear2.value = "";
            });
        }

    } catch (error) {
        console.error("Error loading comparison data:", error);
    }
}

function renderComparison(data) {
    const c1 = data.country1;
    const c2 = data.country2;

    // Update Headers
    document.getElementById('nameC1').textContent = c1.Country_Name;
    document.getElementById('codeC1').textContent = c1.Country_Code;
    document.getElementById('avatarC1').textContent = c1.Country_Name.charAt(0);

    document.getElementById('nameC2').textContent = c2.Country_Name;
    document.getElementById('codeC2').textContent = c2.Country_Code;
    document.getElementById('avatarC2').textContent = c2.Country_Name.charAt(0);

    // Metrics to show
    const metricsMap = [
        { label: "GDP Per Capita ($)", key: "GDP_Per_Capita ($)", icon: "bi-currency-dollar", better: "higher" },
        { label: "Gini Index (0-100)", key: "Gini_Index (0-100)", icon: "bi-graph-up", better: "lower" },
        { label: "Unemployment Rate (%)", key: "Unemployement_Rate (%)", icon: "bi-person-badge", better: "lower" },
        { label: "Middle Class Share", key: "Middle_Class_Income_Share", icon: "bi-people", better: "higher" },
        { label: "Income Share Gap", key: "Income_Share_Gap", icon: "bi-dash-lg", better: "lower" },
        { label: "Lowest 20% Share", key: "Income Share_Lowest 20%", icon: "bi-chevron-double-down", better: "higher" },
        { label: "Highest 20% Share", key: "Income Share_Highest 20%", icon: "bi-chevron-double-up", better: "lower" },
        { label: "Second 20% Share", key: "Income Share_Second 20%", icon: "bi-chevron-down", better: "higher" },
        { label: "Third 20% Share", key: "Income Share_Third 20%", icon: "bi-chevron-expand", better: "higher" },
        { label: "Fourth 20% Share", key: "Income Share_Fourth 20%", icon: "bi-chevron-up", better: "higher" },
        { label: "Continent", key: "Country_Continent", icon: "bi-globe" },
        { label: "Year Group", key: "Year_Group", icon: "bi-calendar3" },
        { label: "GDP Category", key: "GDP_Per_Capita_Category", icon: "bi-tag" },
        { label: "Inequality Level", key: "Gini_Inequality_Level", icon: "bi-exclamation-triangle" },
        { label: "Unemployment Level", key: "Unemployment_Level", icon: "bi-activity" }
    ];

    const getBadge = (val1, val2, type) => {
        if (!type || val1 === null || val2 === null) return '';
        
        if (typeof val1 === 'number' && typeof val2 === 'number') {
            if (val1 === val2) return '';
            const isBetter = type === 'higher' ? (val1 > val2) : (val1 < val2);
            return isBetter ? '<span class="comp-badge badge-better">Better</span>' : '<span class="comp-badge badge-worse">Low</span>';
        }

        if (val1 === val2) return '';
        const isBetterStr = type === 'higher' ? (String(val1) > String(val2)) : (String(val1) < String(val2));
        return isBetterStr ? '<span class="comp-badge badge-better">Better</span>' : '<span class="comp-badge badge-worse">Low</span>';
    };

    const generateTableRows = () => {
        return metricsMap.map((m, index) => {
            const v1 = c1[m.key];
            const v2 = c2[m.key];
            const badge1 = getBadge(v1, v2, m.better);
            const badge2 = getBadge(v2, v1, m.better);

            return `
                <div class="comp-row" data-aos="fade-up" data-aos-delay="${index * 50}">
                    <div class="comp-cell-label">
                        <i class="bi ${m.icon} comp-metric-icon"></i>
                        ${m.label}
                    </div>
                    <!-- Country 1 Value -->
                    <div class="comp-cell comp-cell-value" data-label="${c1.Country_Name}">
                        <div>
                            ${v1 !== null ? (typeof v1 === 'number' ? v1.toLocaleString() : v1) : '--'}
                            ${badge1}
                        </div>
                    </div>
                    <!-- Country 2 Value -->
                    <div class="comp-cell comp-cell-value" data-label="${c2.Country_Name}">
                        <div>
                            ${v2 !== null ? (typeof v2 === 'number' ? v2.toLocaleString() : v2) : '--'}
                            ${badge2}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    };

    document.getElementById('compTableRows').innerHTML = generateTableRows();
}

// Start loading
document.addEventListener('DOMContentLoaded', initDashboard);

// --- New UI Logic for Hub & FAQ ---

/**
 * Toggles between the three major action hub sections.
 */
function toggleHubSection(sectionId, btnElement) {
    document.querySelectorAll('.action-hub-btn').forEach(btn => btn.classList.remove('active'));
    btnElement.classList.add('active');

    document.querySelectorAll('.hub-content').forEach(section => {
        section.classList.add('d-none');
    });

    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.remove('d-none');
        if (typeof AOS !== 'undefined') AOS.refresh();
        
        if (window.innerWidth < 768) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

/**
 * Toggles FAQ answers.
 */
function toggleFaq(faqElement) {
    document.querySelectorAll('.faq-item').forEach(item => {
        if (item !== faqElement) {
            item.classList.remove('active');
            item.querySelector('.faq-answer').classList.add('d-none');
        }
    });

    const answer = faqElement.querySelector('.faq-answer');
    faqElement.classList.toggle('active');
    answer.classList.toggle('d-none');
}

// Ensure first hub section is pre-expanded correctly if visible
document.addEventListener('DOMContentLoaded', () => {
    const comparisonSection = document.getElementById('comparisonSection');
    if (comparisonSection && !comparisonSection.classList.contains('d-none')) {
        const firstBtn = document.querySelector('.action-hub-btn');
        if (firstBtn) firstBtn.classList.add('active');
    }
});

