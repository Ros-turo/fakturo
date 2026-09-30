
const invoicesObject = {
    invoices: [
        { number: "2026-001", client: "ACME s.r.o.", amount: 15000, status: "paid" },
        { number: "2026-002", client: "Car s.r.o.", amount: 3001, status: "draft" },
        { number: "2026-003", client: "Arew.", amount: 750, status: "draft" },
        { number: "2026-004", client: "Fun", amount: 23000, status: "paid" }
    ]
};

const invoiceArticle = document.querySelectorAll(".invoice");
invoiceArticle.forEach((article, index) => {
    const invoiceToSet = invoicesObject.invoices[index];
    if (invoiceToSet.status === "paid") {
        article.classList.add("paid");
    }
    const paragraphs = article.querySelectorAll("p");
    paragraphs.forEach((paragraph, index) => {
        const invoiceRow = Object.values(invoiceToSet)[index];
        paragraph.textContent = `${invoiceRow}`
    })
})