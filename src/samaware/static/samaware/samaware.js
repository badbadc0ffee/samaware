document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.samaware-list-filter input[type="checkbox"]').forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
            checkbox.form.submit()
        })
    })

    document.querySelectorAll('form.samaware-arrived-form').forEach((form) => {
        form.addEventListener('submit', async (ev) => {
            ev.preventDefault()

            if (await toggleArrived(form)) {
                form.querySelectorAll('.samaware-btn').forEach((button) => {
                    button.classList.toggle('d-none')
                })
            }
        })
    })

})


async function toggleArrived(form) {

    try {
        const response = await fetch(form.action)
        if (response.staus >= 400) {
            return false
        }
        return true
    } catch {
        return false
    }

}
