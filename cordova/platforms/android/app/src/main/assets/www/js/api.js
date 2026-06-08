const API_BASE = 'http://123.57.107.21:8088';

async function postItem(formData) {
  const res = await fetch(`${API_BASE}/api/v1/items`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ description: res.statusText }));
    throw new Error(err.description || 'upload failed');
  }
  return res.json();
}

async function listItems(category, limit = 50) {
  let url = `${API_BASE}/api/v1/items?limit=${limit}`;
  if (category && category !== 'all') url += `&category=${category}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('list items failed');
  return res.json();
}

async function getItem(id) {
  const res = await fetch(`${API_BASE}/api/v1/items/${id}`);
  if (!res.ok) throw new Error('get item failed');
  return res.json();
}

async function deleteItem(id) {
  const res = await fetch(`${API_BASE}/api/v1/items/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('delete failed');
  return res.json();
}

async function recommendOutfit(occasion, season, weather, limit = 3) {
  const res = await fetch(`${API_BASE}/api/v1/outfits/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occasion, season, weather, limit }),
  });
  if (!res.ok) throw new Error('recommend failed');
  return res.json();
}

async function getOutfit(id) {
  const res = await fetch(`${API_BASE}/api/v1/outfits/${id}`);
  if (!res.ok) throw new Error('get outfit failed');
  return res.json();
}

async function feedbackOutfit(id, score) {
  const res = await fetch(`${API_BASE}/api/v1/outfits/${id}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score }),
  });
  if (!res.ok) throw new Error('feedback failed');
  return res.json();
}

async function listOutfits(limit = 20) {
  const res = await fetch(`${API_BASE}/api/v1/outfits?limit=${limit}`);
  if (!res.ok) throw new Error('list outfits failed');
  return res.json();
}