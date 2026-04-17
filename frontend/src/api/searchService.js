const API_BASE_URL = '/api'

function appendSearchSettings(formData, settings = {}) {
    if (!settings) return

    if (settings.default_results_per_page != null) {
        formData.append('page_size', settings.default_results_per_page)
    }
    if (settings.similarity_threshold != null) {
        formData.append('similarity_threshold', settings.similarity_threshold)
    }
    if (settings.weights?.semantic != null) {
        formData.append('semantic_weight', settings.weights.semantic)
    }
    if (settings.weights?.design != null) {
        formData.append('design_weight', settings.weights.design)
    }
    if (settings.weights?.color != null) {
        formData.append('color_weight', settings.weights.color)
    }
    if (settings.weights?.texture != null) {
        formData.append('texture_weight', settings.weights.texture)
    }
    if (settings.enable_sub_part_localization != null) {
        formData.append(
            'enable_sub_part_localization',
            settings.enable_sub_part_localization,
        )
    }
}

export async function searchImage(file, settings) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('page', 1)
    appendSearchSettings(formData, settings)

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
    }

    return await response.json()
}

export async function searchNextPage(queryId, page, settings) {
    const formData = new FormData()
    formData.append('query_id', queryId)
    formData.append('page', page)
    if (settings?.default_results_per_page != null) {
        formData.append('page_size', settings.default_results_per_page)
    }

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Failed to load page ${page}: ${response.statusText}`)
    }

    return await response.json()
}

export async function fetchSearchSettings() {
    const response = await fetch(`${API_BASE_URL}/settings/search`)

    if (!response.ok) {
        throw new Error(`Failed to load settings: ${response.statusText}`)
    }

    return await response.json()
}

export async function updateSearchSettings(settings) {
    const response = await fetch(`${API_BASE_URL}/settings/search`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
    })

    if (!response.ok) {
        throw new Error(`Failed to save settings: ${response.statusText}`)
    }

    return await response.json()
}

export async function syncBucket() {
    const response = await fetch(`${API_BASE_URL}/sync_bucket`, {
        method: 'POST',
    })

    if (!response.ok) {
        throw new Error(`Sync failed: ${response.statusText}`)
    }

    return await response.json()
}

export const fetchGallery = async (page = 1, pageSize = 50, q = '') => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (q) params.append('q', q);

    const response = await fetch(`${API_BASE_URL}/gallery?${params.toString()}`);

    if (!response.ok) {
        throw new Error(`Failed to load gallery: ${response.statusText}`)
    }

    return await response.json()
}

export async function deleteGalleryItems(objectKeys) {
    const response = await fetch(`${API_BASE_URL}/gallery`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ object_keys: objectKeys }),
    })

    if (!response.ok) {
        throw new Error(`Delete failed: ${response.statusText}`)
    }

    return await response.json()
}
