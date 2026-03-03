const API_BASE_URL = '/api'

export async function searchImage(file, pageSize = 50, similarityThreshold = 0.0) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('page', 1)
    formData.append('page_size', pageSize)
    formData.append('similarity_threshold', similarityThreshold)

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
    }

    return await response.json()
}

export async function searchNextPage(queryId, page, pageSize = 50, similarityThreshold = 0.0) {
    const formData = new FormData()
    formData.append('query_id', queryId)
    formData.append('page', page)
    formData.append('page_size', pageSize)
    formData.append('similarity_threshold', similarityThreshold)

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Failed to load page ${page}: ${response.statusText}`)
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

export async function fetchGallery(page = 1, pageSize = 50) {
    const response = await fetch(
        `${API_BASE_URL}/gallery?page=${page}&page_size=${pageSize}`
    )

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
