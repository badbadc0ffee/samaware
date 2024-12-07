document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.samaware-list-filter input[type="checkbox"]').forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
            checkbox.form.submit()
        })
    })

})
