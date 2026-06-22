// app.js

// 1. Supabase client
const SUPABASE_URL = "https://qengelpsbofurqhmbpew.supabase.co";
const SUPABASE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFlbmdlbHBzYm9mdXJxaG1icGV3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE5NDA0MTEsImV4cCI6MjA5NzUxNjQxMX0.-5MnRSDK9zREj89SPUhwKdolzu9yf9hEcvwJUTTPL9Y";

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// 1a. Overlay elements
const zoomOverlay = document.getElementById("zoom-overlay");
const zoomImage = document.getElementById("zoom-image");
const zoomCaption = document.getElementById("zoom-caption");
const zoomBody = document.getElementById("zoom-body");
const zoomCloseBtn = document.getElementById("zoom-close");

if (zoomCloseBtn) {
  zoomCloseBtn.addEventListener("click", closeZoom);
}
if (zoomOverlay) {
  zoomOverlay.addEventListener("click", (e) => {
    if (e.target === zoomOverlay || e.target.classList.contains("zoom-backdrop")) {
      closeZoom();
    }
  });
}

function openZoom(src, caption) {
  if (src) {
    zoomImage.src = src;
    zoomImage.alt = caption;
    zoomImage.style.display = "block";
  } else if (zoomImage) {
    zoomImage.style.display = "none";
  }
  if (zoomCaption) zoomCaption.textContent = caption;
  if (zoomBody) zoomBody.innerHTML = "";
  if (zoomOverlay) zoomOverlay.classList.add("visible");
}

function closeZoom() {
  if (zoomOverlay) zoomOverlay.classList.remove("visible");
}

// 2. Navigation
const navButtons = document.querySelectorAll(".nav-btn");
const pages = document.querySelectorAll(".page");
const statusIndicator = document.getElementById("status-indicator");
const statusText = document.getElementById("status-text");

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.getAttribute("data-page");
    setActiveNav(target);
    showPage(target);
  });
});

function setActiveNav(pageId) {
  navButtons.forEach((btn) => {
    const p = btn.getAttribute("data-page");
    btn.classList.toggle("active", p === pageId);
  });
}

function showPage(pageId) {
  pages.forEach((page) => {
    page.classList.toggle("visible", page.id === `page-${pageId}`);
  });
}

// 3. INIT (main entry)
async function initApp() {
  await checkConnectionAndLoadDashboard();
  await loadRacks();
  await initUsePage();
  await initHistoryPage();
  await initAdjustPage();
  
  // Add submit
  const addSubmit = document.getElementById("add-submit");
  if (addSubmit) addSubmit.addEventListener("click", onAddSubmit);

  // Manage search
  initManageSearch();
  initEmployeesPage();
}

// 3a. Connection + dashboard
async function checkConnectionAndLoadDashboard() {
  try {
    const { error } = await supabase.from("stocks").select("quantity").limit(1);
    if (error) throw error;
    setOnline(true);
    await loadDashboard();
  } catch (e) {
    console.error(e);
    setOnline(false);
  }
}

function setOnline(isOnline) {
  if (!statusIndicator || !statusText) return;
  statusIndicator.className = "status " + (isOnline ? "online" : "offline");
  statusText.textContent = isOnline ? "Online" : "Offline";
}

// 4. Dashboard
async function loadDashboard() {
  try {
    const totalItemsEl = document.getElementById("total-items");
    const lowStockEl = document.getElementById("low-stock-count");
    const recentCountEl = document.getElementById("recent-activity-count");
    const tbody = document.querySelector("#recent-table tbody");

    const { data: stocks } = await supabase.from("stocks").select("quantity");
    const total = (stocks || []).reduce(
      (sum, row) => sum + (row.quantity || 0),
      0
    );
    if (totalItemsEl) totalItemsEl.textContent = total;

    const { data: allStocks } = await supabase
      .from("stocks")
      .select("component_id, quantity");
    const totals = {};
    (allStocks || []).forEach((row) => {
      totals[row.component_id] =
        (totals[row.component_id] || 0) + (row.quantity || 0);
    });
    const lowCount = Object.values(totals).filter((q) => q <= 5).length;
    if (lowStockEl) lowStockEl.textContent = lowCount;

    const { data: moves } = await supabase
      .from("stock_movements")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(10);

    if (tbody) {
      tbody.innerHTML = "";
      (moves || []).forEach((mv) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${mv.movement_date || ""}</td>
          <td>${mv.movement_type}</td>
          <td>${mv.component_id}</td>
          <td>${mv.from_location_id || mv.to_location_id || ""}</td>
          <td>${mv.quantity}</td>
          <td>${mv.user_name || ""}</td>
        `;
        tbody.appendChild(tr);
      });
    }
    if (recentCountEl) recentCountEl.textContent = moves?.length || 0;
  } catch (e) {
    console.error("loadDashboard error", e);
  }
}

// 5. Shared helpers
function normalizeKey(text) {
  return text.trim().toUpperCase().replace(/\s+/g, "_");
}

function prettyName(text) {
  if (!text) return "";
  return text
    .replace(/_/g, " ")
    .toLowerCase()
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function todayISTDateString() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function nowISO() {
  return new Date().toISOString();
}

// 6. Manage: racks / shelves / components (current-shelf search)
let manageComponentsCache = []; // components for current shelf

async function loadRacks() {
  try {
    const rackList = document.getElementById("rack-list");
    if (!rackList) return;

    const { data, error } = await supabase
      .from("locations")
      .select("id, location_key, display_name");
    if (error) throw error;

    const racksMap = {};
    (data || []).forEach((row) => {
      const key = row.location_key || "";
      const parts = key.split("_");
      if (!parts.length) return;
      const rackKey = parts[0]; // e.g. RACK1
      if (!rackKey) return;
      if (!racksMap[rackKey]) {
        racksMap[rackKey] = {
          rackKey,
          rackName: prettyName(rackKey),
        };
      }
    });

    rackList.innerHTML = "";
    Object.values(racksMap).forEach((rack) => {
      const card = document.createElement("div");
      card.className = "rack-card";

      const label = document.createElement("div");
      label.className = "rack-card-label";
      label.textContent = rack.rackName;

      card.appendChild(label);

      card.addEventListener("click", () => {
        openZoom("", `Rack: ${rack.rackName}`);
        onRackSelected(rack.rackKey, true);
      });

      rackList.appendChild(card);
    });
  } catch (e) {
    console.error("loadRacks error:", e);
  }
}

async function onRackSelected(rackKey, intoOverlay = false) {
  const prefix = normalizeKey(rackKey) + "_";
  try {
    const { data, error } = await supabase
      .from("locations")
      .select("id, location_key, display_name")
      .like("location_key", `${prefix}%`);
    if (error) throw error;

    const shelvesMap = {};
    (data || []).forEach((row) => {
      const parts = (row.location_key || "").split("_");
      if (parts.length < 2) return;
      const shelfKey = parts[1]; // e.g. SHELF1
      if (!shelfKey) return;
      if (!shelvesMap[shelfKey]) {
        shelvesMap[shelfKey] = {
          shelfKey,
          shelfName: prettyName(shelfKey),
        };
      }
    });

    if (intoOverlay && zoomBody) {
      zoomBody.innerHTML = "";
      const shelfContainer = document.createElement("div");
      shelfContainer.className = "manage-layout";

      Object.values(shelvesMap).forEach((shelf) => {
        const card = document.createElement("div");
        card.className = "shelf-card";

        const label = document.createElement("div");
        label.className = "shelf-card-label";
        label.textContent = shelf.shelfName;

        card.appendChild(label);

        card.addEventListener("click", () =>
          onShelfSelected(rackKey, shelf.shelfKey, true)
        );

        shelfContainer.appendChild(card);
      });

      if (!Object.keys(shelvesMap).length) {
        shelfContainer.innerHTML =
          "<div class='placeholder'>No shelves found for this rack.</div>";
      }

      zoomBody.appendChild(shelfContainer);
    }
  } catch (e) {
    console.error("onRackSelected error:", e);
  }
}

async function onShelfSelected(rackKey, shelfKey, intoOverlay = false) {
  const prefix = `${normalizeKey(rackKey)}_${normalizeKey(shelfKey)}`;
  try {
    const { data: locs, error: locErr } = await supabase
      .from("locations")
      .select("id, location_key")
      .like("location_key", `${prefix}%`);
    if (locErr) throw locErr;

    const locationIds = (locs || []).map((l) => l.id);
    if (!locationIds.length) {
      if (intoOverlay && zoomBody) {
        zoomBody.innerHTML =
          "<div class='placeholder'>No locations for this shelf.</div>";
      }
      return;
    }

    const { data: stocks, error: stErr } = await supabase
      .from("stocks")
      .select(
        "id, quantity, location_id, components(id, component_name_raw, part_number_raw, photo_url)"
      )
      .in("location_id", locationIds);
    if (stErr) throw stErr;

    if (intoOverlay && zoomBody) {
      zoomBody.innerHTML = "";
      manageComponentsCache = stocks || [];
      clearManageSearch();

      if (zoomImage) zoomImage.style.display = "none";
      if (zoomCaption)
        zoomCaption.textContent = `Shelf: ${prettyName(shelfKey)}`;

      renderManageComponents(manageComponentsCache, zoomBody);
    }
  } catch (e) {
    console.error("onShelfSelected error:", e);
    if (intoOverlay && zoomBody) {
      zoomBody.innerHTML =
        "<div class='placeholder'>Failed to load components.</div>";
    }
  }
}

function renderManageComponents(entries, containerOverride) {
  const target =
    containerOverride || document.getElementById("manage-components");
  if (!target) return;

  target.innerHTML = "";
  if (!entries || !entries.length) {
    target.innerHTML =
      "<div class='placeholder'>No components on this shelf.</div>";
    return;
  }

  (entries || []).forEach((row) => {
    const comp = row.components;
    const name = prettyName(comp.component_name_raw);
    const part = prettyName(comp.part_number_raw);
    const qty = row.quantity || 0;
    const photoUrl = comp.photo_url || "";

    const card = document.createElement("div");
    card.className = "component-card";

    if (photoUrl) {
      const img = document.createElement("img");
      img.src = photoUrl;
      img.alt = name;
      img.className = "component-img";
      card.appendChild(img);
    }

    const title = document.createElement("div");
    title.className = "component-name";
    title.textContent = name;

    const partEl = document.createElement("div");
    partEl.className = "component-part";
    partEl.textContent = part;

    const qtyEl = document.createElement("div");
    qtyEl.className = "component-qty";
    qtyEl.textContent = `Qty: ${qty}`;

    card.appendChild(title);
    card.appendChild(partEl);
    card.appendChild(qtyEl);

    target.appendChild(card);
  });
}

// Manage search (current shelf only)
function initManageSearch() {
  const input = document.getElementById("manage-search");
  if (!input) return;

  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (!zoomBody) return;

    if (!q) {
      renderManageComponents(manageComponentsCache, zoomBody);
      return;
    }
    const filtered = (manageComponentsCache || []).filter((row) => {
      const comp = row.components;
      const name = prettyName(comp.component_name_raw).toLowerCase();
      const part = prettyName(comp.part_number_raw).toLowerCase();
      return name.includes(q) || part.includes(q);
    });
    renderManageComponents(filtered, zoomBody);
  });
}

function clearManageSearch() {
  const input = document.getElementById("manage-search");
  if (input) input.value = "";
}

// 7. ADD / RECEIVE (photo_url stored)
async function ensureLocation(rack, shelf, position) {
  const rackKey = normalizeKey(rack);
  const shelfKey = normalizeKey(shelf);
  let locKey;
  let display;
  if (position) {
    const posKey = normalizeKey(position);
    locKey = `${rackKey}_${shelfKey}_${posKey}`;
    display = `${prettyName(rackKey)} / ${prettyName(
      shelfKey
    )} / ${prettyName(posKey)}`;
  } else {
    locKey = `${rackKey}_${shelfKey}`;
    display = `${prettyName(rackKey)} / ${prettyName(shelfKey)}`;
  }

  let { data, error } = await supabase
    .from("locations")
    .select("id")
    .eq("location_key", locKey)
    .limit(1);
  if (error) throw error;
  if (data && data.length > 0) {
    return data[0].id;
  }

  const insertData = {
    location_key: locKey,
    display_name: display,
    created_at: nowISO(),
  };
  ({ data, error } = await supabase
    .from("locations")
    .insert(insertData)
    .select("id")
    .single());
  if (error) throw error;
  return data.id;
}

async function upsertComponentAndReceiveStock({
  vendor,
  name,
  part,
  qty,
  purpose,
  remarks,
  locationId,
  photoUrl,
}) {
  const ts = nowISO();
  const cnameRaw = normalizeKey(name);
  const partRaw = part ? normalizeKey(part) : null;
  const compKey = cnameRaw + "_" + (partRaw || "NO_PART");

  let { data, error } = await supabase
    .from("components")
    .select("*")
    .eq("component_key", compKey);
  if (error) throw error;

  let compId;
  if (data && data.length > 0) {
    compId = data[0].id;
    const updateData = {
      vendor_name: vendor,
      purpose_of_purchase: purpose,
      remarks,
      updated_at: ts,
    };
    if (photoUrl) {
      updateData.photo_url = photoUrl;
    }
    const { error: uErr } = await supabase
      .from("components")
      .update(updateData)
      .eq("id", compId);
    if (uErr) throw uErr;
  } else {
    const insertData = {
      component_key: compKey,
      component_name_raw: cnameRaw,
      part_number_raw: partRaw,
      vendor_name: vendor,
      purpose_of_purchase: purpose,
      remarks,
      photo_url: photoUrl || null,
      created_at: ts,
      updated_at: ts,
    };
    const res = await supabase
      .from("components")
      .insert(insertData)
      .select("id")
      .single();
    if (res.error) throw res.error;
    compId = res.data.id;
  }

  const resStock = await supabase
    .from("stocks")
    .select("*")
    .eq("component_id", compId)
    .eq("location_id", locationId);
  if (resStock.error) throw resStock.error;

  if (resStock.data && resStock.data.length > 0) {
    const row = resStock.data[0];
    const newQty = (row.quantity || 0) + qty;
    const { error: sErr } = await supabase
      .from("stocks")
      .update({ quantity: newQty, updated_at: ts })
      .eq("id", row.id);
    if (sErr) throw sErr;
  } else {
    const { error: sErr } = await supabase.from("stocks").insert({
      component_id: compId,
      location_id: locationId,
      quantity: qty,
      updated_at: ts,
    });
    if (sErr) throw sErr;
  }

  const mvData = {
    component_id: compId,
    from_location_id: null,
    to_location_id: locationId,
    quantity: qty,
    movement_type: "ADD",
    user_name: "WEB_UI",
    purpose,
    remarks,
    movement_date: todayISTDateString(),
    created_at: ts,
  };
  const { error: mErr } = await supabase
    .from("stock_movements")
    .insert(mvData);
  if (mErr) throw mErr;
}

async function onAddSubmit() {
  const vendor = document.getElementById("add-vendor")?.value.trim() || "";
  const name = document.getElementById("add-name")?.value.trim() || "";
  const part = document.getElementById("add-part")?.value.trim() || "";
  const rack = document.getElementById("add-rack")?.value.trim() || "";
  const shelf = document.getElementById("add-shelf")?.value.trim() || "";
  const position =
    document.getElementById("add-position")?.value.trim() || "";
  const qty =
    parseInt(document.getElementById("add-qty")?.value, 10) || 0;
  const purpose =
    document.getElementById("add-purpose")?.value.trim() || "";
  const remarks =
    document.getElementById("add-remarks")?.value.trim() || "";
  const photoUrl =
    document.getElementById("add-photo")?.value.trim() || "";

  if (!name || !rack || !shelf || qty <= 0) {
    alert("Component name, rack, shelf, and positive quantity are required.");
    return;
  }

  try {
    const locId = await ensureLocation(rack, shelf, position || null);
    await upsertComponentAndReceiveStock({
      vendor,
      name,
      part: part || null,
      qty,
      purpose,
      remarks,
      locationId: locId,
      photoUrl: photoUrl || null,
    });

    alert("Component added and stock received.");
    [
      "add-vendor",
      "add-name",
      "add-part",
      "add-rack",
      "add-shelf",
      "add-position",
      "add-qty",
      "add-purpose",
      "add-remarks",
      "add-photo",
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    await loadDashboard();
    await loadRacks();
  } catch (e) {
    console.error("Add error:", e);
    alert("Failed to add component. Check console for details.");
  }
}

// 8. USE

async function getLocations() {
  const { data, error } = await supabase
    .from("locations")
    .select("*")
    .order("display_name");
  if (error) throw error;
  return data || [];
}

async function getComponentsWithStockAtLocation(locationId) {
  const { data, error } = await supabase
    .from("stocks")
    .select(
      "id, quantity, location_id, components(id, component_name_raw, part_number_raw)"
    )
    .eq("location_id", locationId)
    .gt("quantity", 0);
  if (error) throw error;
  return data || [];
}

async function loadEmployees() {
  const { data, error } = await supabase
    .from("employees")
    .select("name")
    .order("name");
  if (error) {
    console.error("loadEmployees error:", error);
    return [];
  }
  return data || [];
}

async function initUsePage() {
  try {
    // Employees dropdown
    const employees = await loadEmployees();
    const userSelect = document.getElementById("use-user");
    if (userSelect) {
      userSelect.innerHTML = "";
      employees.forEach((emp) => {
        const opt = document.createElement("option");
        opt.value = emp.name;
        opt.textContent = emp.name;
        userSelect.appendChild(opt);
      });
    }

    // Locations + components
    const locations = await getLocations();
    const locSelect = document.getElementById("use-location");
    if (!locSelect) return;

    locSelect.innerHTML = "";
    locations.forEach((loc) => {
      const option = document.createElement("option");
      option.value = String(loc.id);
      option.textContent = loc.display_name;
      locSelect.appendChild(option);
    });

    if (locations.length) {
      await loadUseComponentsForLocation(locations[0].id);
    }

    locSelect.addEventListener("change", async (e) => {
      const id = parseInt(e.target.value, 10);
      if (!isNaN(id)) {
        await loadUseComponentsForLocation(id);
      }
    });

    const useSubmit = document.getElementById("use-submit");
    if (useSubmit) useSubmit.addEventListener("click", onUseSubmit);
  } catch (e) {
    console.error("initUsePage error:", e);
  }
}

async function loadUseComponentsForLocation(locationId) {
  const compSelect = document.getElementById("use-component");
  if (!compSelect) return;
  compSelect.innerHTML = "";
  try {
    const entries = await getComponentsWithStockAtLocation(locationId);
    entries.forEach((row, idx) => {
      const comp = row.components;
      const name = prettyName(comp.component_name_raw);
      const part = prettyName(comp.part_number_raw);
      const qty = row.quantity || 0;
      const opt = document.createElement("option");
      opt.value = String(idx);
      opt.textContent = `${name} (${part}) - Qty: ${qty}`;
      compSelect.appendChild(opt);
    });
    compSelect._entries = entries;
  } catch (e) {
    console.error("loadUseComponentsForLocation error:", e);
  }
}

async function onUseSubmit() {
  const user = document.getElementById("use-user")?.value.trim() || "";
  const locId = parseInt(
    document.getElementById("use-location")?.value,
    10
  );
  const compSelect = document.getElementById("use-component");
  const compIdx = parseInt(compSelect?.value, 10);
  const qty =
    parseInt(document.getElementById("use-qty")?.value, 10) || 0;
  const purpose =
    document.getElementById("use-purpose")?.value.trim() || "";
  const dateVal =
    document.getElementById("use-date")?.value || "";
  const remarks =
    document.getElementById("use-remarks")?.value.trim() || "";

  if (!user || isNaN(locId) || isNaN(compIdx)) {
    alert("User, location, and component are required.");
    return;
  }
  if (qty <= 0) {
    alert("Quantity must be greater than zero.");
    return;
  }

  const entries = compSelect._entries || [];
  const entry = entries[compIdx];
  if (!entry) {
    alert("Invalid component selection.");
    return;
  }

  const available = entry.quantity || 0;
  if (qty > available) {
    alert(`Requested ${qty}, but only ${available} available.`);
    return;
  }

  const useDate = dateVal || todayISTDateString();

  try {
    await useStock(
      entry.components.id,
      entry.id,
      locId,
      qty,
      user,
      purpose,
      useDate,
      remarks
    );
    alert("Usage logged.");
    const ids = ["use-qty", "use-purpose", "use-date", "use-remarks"];
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    await loadUseComponentsForLocation(locId);
    await loadDashboard();
  } catch (e) {
    console.error("onUseSubmit error:", e);
    alert("Failed to log usage.");
  }
}

async function useStock(
  componentId,
  stockId,
  locationId,
  qty,
  userName,
  purpose,
  dateStr,
  remarks
) {
  const ts = nowISO();

  const { data, error } = await supabase
    .from("stocks")
    .select("quantity")
    .eq("id", stockId)
    .single();
  if (error) throw error;
  const current = data.quantity || 0;
  const newQty = Math.max(current - qty, 0);

  const { error: uErr } = await supabase
    .from("stocks")
    .update({ quantity: newQty, updated_at: ts })
    .eq("id", stockId);
  if (uErr) throw uErr;

  const mvData = {
    component_id: componentId,
    from_location_id: locationId,
    to_location_id: null,
    quantity: qty,
    movement_type: "USE",
    user_name: userName,
    purpose,
    remarks,
    movement_date: dateStr,
    created_at: ts,
  };
  const { error: mErr } = await supabase
    .from("stock_movements")
    .insert(mvData);
  if (mErr) throw mErr;
}

// 9. HISTORY
async function initHistoryPage() {
  const applyBtn = document.getElementById("history-apply");
  const exportBtn = document.getElementById("history-export");

  if (applyBtn) applyBtn.addEventListener("click", loadHistory);
  if (exportBtn) exportBtn.addEventListener("click", exportHistoryCsv);

  await loadHistory();
}

async function loadHistory() {
  const from = document.getElementById("history-from")?.value || null;
  const to = document.getElementById("history-to")?.value || null;
  const type = document.getElementById("history-type")?.value;
  const search =
    document.getElementById("history-search")?.value.trim() || "";

  try {
    let query = supabase
      .from("stock_movements")
      .select("*")
      .order("created_at", { ascending: false });

    if (from) query = query.gte("movement_date", from);
    if (to) query = query.lte("movement_date", to);
    if (type && type !== "ALL") query = query.eq("movement_type", type);

    const { data, error } = await query;
    if (error) throw error;

    let rows = data || [];
    if (search) {
      const s = search.toLowerCase();
      rows = rows.filter((mv) =>
        ((mv.purpose || "") + " " + (mv.remarks || "")).toLowerCase().includes(s)
      );
    }

    window._historyRows = rows;

    const tbody = document.querySelector("#history-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    rows.forEach((mv) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${mv.movement_date || ""}</td>
        <td>${mv.movement_type}</td>
        <td>${mv.component_id}</td>
        <td>${mv.from_location_id || ""}</td>
        <td>${mv.to_location_id || ""}</td>
        <td>${mv.quantity}</td>
        <td>${mv.user_name || ""}</td>
        <td>${(mv.purpose || "").slice(0, 60)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("loadHistory error:", e);
  }
}

function exportHistoryCsv() {
  const rows = window._historyRows || [];
  if (!rows.length) {
    alert("No history to export.");
    return;
  }

  const headers = [
    "movement_date",
    "movement_type",
    "component_id",
    "from_location_id",
    "to_location_id",
    "quantity",
    "user_name",
    "purpose",
    "remarks",
    "created_at",
  ];

  const lines = [headers.join(",")];
  rows.forEach((mv) => {
    const line = headers
      .map((h) => {
        const v = mv[h] ?? "";
        const s = String(v).replace(/"/g, '""');
        return `"${s}"`;
      })
      .join(",");
    lines.push(line);
  });

  const blob = new Blob([lines.join("\n")], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "stock_history.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 10. ADJUST
async function initAdjustPage() {
  try {
    const locations = await getLocations();
    const locSelect = document.getElementById("adjust-location");
    if (!locSelect) return;

    locSelect.innerHTML = "";
    locations.forEach((loc) => {
      const option = document.createElement("option");
      option.value = String(loc.id);
      option.textContent = loc.display_name;
      locSelect.appendChild(option);
    });

    if (locations.length) {
      await loadAdjustComponentsForLocation(locations[0].id);
    }

    locSelect.addEventListener("change", async (e) => {
      const id = parseInt(e.target.value, 10);
      if (!isNaN(id)) {
        await loadAdjustComponentsForLocation(id);
      }
    });

    const compSelect = document.getElementById("adjust-component");
    if (compSelect) {
      compSelect.addEventListener("change", onAdjustComponentChange);
    }

    const adjustSubmit = document.getElementById("adjust-submit");
    if (adjustSubmit) adjustSubmit.addEventListener("click", onAdjustSubmit);
  } catch (e) {
    console.error("initAdjustPage error:", e);
  }
}

async function loadAdjustComponentsForLocation(locationId) {
  const compSelect = document.getElementById("adjust-component");
  if (!compSelect) return;
  compSelect.innerHTML = "";
  try {
    const { data, error } = await supabase
      .from("stocks")
      .select(
        "id, quantity, location_id, components(id, component_name_raw, part_number_raw)"
      )
      .eq("location_id", locationId);
    if (error) throw error;

    (data || []).forEach((se, idx) => {
      const comp = se.components;
      const name = prettyName(comp.component_name_raw);
      const part = prettyName(comp.part_number_raw);
      const qty = se.quantity || 0;
      const opt = document.createElement("option");
      opt.value = String(idx);
      opt.textContent = `${name} (${part}) - Qty: ${qty}`;
      compSelect.appendChild(opt);
    });
    compSelect._entries = data || [];

    onAdjustComponentChange();
  } catch (e) {
    console.error("loadAdjustComponentsForLocation error:", e);
  }
}

function onAdjustComponentChange() {
  const compSelect = document.getElementById("adjust-component");
  const idx = parseInt(compSelect?.value, 10);
  const entries = compSelect?._entries || [];
  const entry = entries[idx];
  const currInput = document.getElementById("adjust-current");
  if (!currInput) return;
  if (!entry) {
    currInput.value = "0";
  } else {
    currInput.value = String(entry.quantity || 0);
  }
}

async function onAdjustSubmit() {
  const user = document.getElementById("adjust-user")?.value.trim() || "";
  const locId = parseInt(
    document.getElementById("adjust-location")?.value,
    10
  );
  const compSelect = document.getElementById("adjust-component");
  const idx = parseInt(compSelect?.value, 10);
  const entries = compSelect?._entries || [];
  const entry = entries[idx];
  const newQty =
    parseInt(document.getElementById("adjust-new")?.value, 10) ?? NaN;
  const reason =
    document.getElementById("adjust-reason")?.value.trim() || "";

  if (!user || isNaN(locId) || !entry) {
    alert("User, location, and component are required.");
    return;
  }
  if (isNaN(newQty) || newQty < 0) {
    alert("New quantity must be a non-negative integer.");
    return;
  }
  if (!reason) {
    if (
      !confirm(
        "No reason provided. It's recommended to record a reason. Continue?"
      )
    ) {
      return;
    }
  }

  try {
    await adjustStock(entry.id, entry.components.id, locId, newQty, user, reason);
    alert("Stock adjusted.");
    const ids = ["adjust-new", "adjust-reason"];
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    await loadAdjustComponentsForLocation(locId);
    await loadDashboard();
  } catch (e) {
    console.error("onAdjustSubmit error:", e);
    alert("Failed to adjust stock.");
  }
}

async function adjustStock(
  stockId,
  componentId,
  locationId,
  newQty,
  userName,
  reason
) {
  const ts = nowISO();

  const { data, error } = await supabase
    .from("stocks")
    .select("quantity")
    .eq("id", stockId)
    .single();
  if (error) throw error;
  const current = data.quantity || 0;
  const diff = newQty - current;

  const { error: uErr } = await supabase
    .from("stocks")
    .update({ quantity: newQty, updated_at: ts })
    .eq("id", stockId);
  if (uErr) throw uErr;

  if (diff !== 0) {
    const mvData = {
      component_id: componentId,
      from_location_id: diff < 0 ? locationId : null,
      to_location_id: diff > 0 ? locationId : null,
      quantity: Math.abs(diff),
      movement_type: "ADJUST",
      user_name: userName,
      purpose: reason,
      remarks: "",
      movement_date: todayISTDateString(),
      created_at: ts,
    };
    const { error: mErr } = await supabase
      .from("stock_movements")
      .insert(mvData);
    if (mErr) throw mErr;
  }
}

// 12. EMPLOYEES (password-protected CRUD)

let employeesCache = [];
let employeesEditId = null;

// Load employees into table and dropdown
async function loadEmployeesTableAndDropdown() {
  try {
    const { data, error } = await supabase
      .from("employees")
      .select("id, name, active")
      .order("name");
    if (error) throw error;

    employeesCache = data || [];

    // Fill table
    const tbody = document.querySelector("#employees-table tbody");
    if (tbody) {
      tbody.innerHTML = "";
      employeesCache.forEach((emp) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${emp.id}</td>
          <td>${emp.name}</td>
          <td>${emp.active ? "Yes" : "No"}</td>
          <td>
            <button class="btn-small" data-action="edit" data-id="${emp.id}">Edit</button>
            <button class="btn-small" data-action="toggle" data-id="${emp.id}">${emp.active ? "Deactivate" : "Activate"}</button>
            <button class="btn-small danger" data-action="delete" data-id="${emp.id}">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      // Attach action handlers
      tbody.querySelectorAll("button[data-action]").forEach((btn) => {
        btn.addEventListener("click", onEmployeesTableAction);
      });
    }

    // Also update Use dropdown
    const userSelect = document.getElementById("use-user");
    if (userSelect) {
      userSelect.innerHTML = "";
      employeesCache
        .filter((e) => e.active !== false)
        .forEach((emp) => {
          const opt = document.createElement("option");
          opt.value = emp.name;
          opt.textContent = emp.name;
          userSelect.appendChild(opt);
        });
    }
  } catch (e) {
    console.error("loadEmployeesTableAndDropdown error:", e);
  }
}

function initEmployeesPage() {
  const loginBtn = document.getElementById("employees-login-btn");
  const pwdInput = document.getElementById("employees-password");
  const loginPanel = document.getElementById("employees-login-panel");
  const panel = document.getElementById("employees-panel");

  const addBtn = document.getElementById("employees-add-btn");
  const saveBtn = document.getElementById("employees-save-btn");
  const cancelBtn = document.getElementById("employees-cancel-btn");
  const nameInput = document.getElementById("employees-name-input");

  if (!loginBtn || !pwdInput || !loginPanel || !panel) return;

  loginBtn.addEventListener("click", () => {
    const pwd = pwdInput.value;
    if (pwd === getAdminPassword()) {
      loginPanel.style.display = "none";
      panel.style.display = "block";
      loadEmployeesTableAndDropdown();
    } else {
      alert("Incorrect password.");
    }
  });

  if (addBtn && nameInput) {
    addBtn.addEventListener("click", async () => {
      const name = nameInput.value.trim();
      if (!name) {
        alert("Name required");
        return;
      }
      try {
        const { error } = await supabase
          .from("employees")
          .insert({ name, active: true });
        if (error) throw error;
        nameInput.value = "";
        employeesEditId = null;
        setEmployeesEditMode(false);
        await loadEmployeesTableAndDropdown();
        alert("Employee added.");
      } catch (e) {
        console.error("add employee error", e);
        alert("Failed to add employee.");
      }
    });
  }

  if (saveBtn && nameInput) {
    saveBtn.addEventListener("click", async () => {
      const name = nameInput.value.trim();
      if (!name) {
        alert("Name required");
        return;
      }
      if (!employeesEditId) {
        alert("No employee selected for edit.");
        return;
      }
      try {
        const { error } = await supabase
          .from("employees")
          .update({ name })
          .eq("id", employeesEditId);
        if (error) throw error;
        nameInput.value = "";
        employeesEditId = null;
        setEmployeesEditMode(false);
        await loadEmployeesTableAndDropdown();
        alert("Employee updated.");
      } catch (e) {
        console.error("update employee error", e);
        alert("Failed to update employee.");
      }
    });
  }

  if (cancelBtn && nameInput) {
    cancelBtn.addEventListener("click", () => {
      nameInput.value = "";
      employeesEditId = null;
      setEmployeesEditMode(false);
    });
  }
}

function setEmployeesEditMode(editing) {
  const addBtn = document.getElementById("employees-add-btn");
  const saveBtn = document.getElementById("employees-save-btn");
  const cancelBtn = document.getElementById("employees-cancel-btn");

  if (addBtn) addBtn.disabled = editing;
  if (saveBtn) saveBtn.disabled = !editing;
  if (cancelBtn) cancelBtn.disabled = !editing;
}

function onEmployeesTableAction(e) {
  const btn = e.currentTarget;
  const id = parseInt(btn.getAttribute("data-id"), 10);
  const action = btn.getAttribute("data-action");
  const emp = employeesCache.find((e) => e.id === id);
  const nameInput = document.getElementById("employees-name-input");

  if (!emp) return;

  if (action === "edit") {
    if (nameInput) nameInput.value = emp.name;
    employeesEditId = emp.id;
    setEmployeesEditMode(true);
  } else if (action === "toggle") {
    const newActive = !emp.active;
    if (!confirm(`Set ${emp.name} to ${newActive ? "Active" : "Inactive"}?`)) {
      return;
    }
    supabase
      .from("employees")
      .update({ active: newActive })
      .eq("id", emp.id)
      .then(() => loadEmployeesTableAndDropdown())
      .catch((err) => {
        console.error("toggle employee error", err);
        alert("Failed to update employee.");
      });
  } else if (action === "delete") {
    if (
      !confirm(
        `Delete employee "${emp.name}"? This cannot be undone.`
      )
    ) {
      return;
    }
    supabase
      .from("employees")
      .delete()
      .eq("id", emp.id)
      .then(() => loadEmployeesTableAndDropdown())
      .catch((err) => {
        console.error("delete employee error", err);
        alert("Failed to delete employee.");
      });
  }
}

function decodeBase64(str) {
  return atob(str);
}

function getAdminPassword() {
  const encoded = "TmF2dGVqQDIwMjY=";
  return decodeBase64(encoded);
}

// 11. Kick off
initApp();