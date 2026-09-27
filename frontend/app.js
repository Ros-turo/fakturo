const newInvoice = document.querySelector("#invoice_create_form");


newInvoice.addEventListener("submit", (event) => {
    event.preventDefault();
    const invoiceData = {};
    newInvoice.querySelectorAll("input, select").forEach(input => {
        if (input.type === "checkbox") {
            invoiceData[input.name] = input.checked;
        }
        else{
            invoiceData[input.name] = input.value;
        }
    })
    console.log(invoiceData);
});

