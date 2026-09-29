import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CREDITS } from "@/lib/credits";

export default function CreditsPage() {
  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Credits</h1>
        <p className="text-muted-foreground">
          Sample photos used in the demo project are from Wikimedia Commons, under the licenses below.
        </p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>File</TableHead>
            <TableHead>Author</TableHead>
            <TableHead>License</TableHead>
            <TableHead>Source</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {CREDITS.map((c) => (
            <TableRow key={c.file}>
              <TableCell className="max-w-64 truncate">{c.file}</TableCell>
              <TableCell>{c.author}</TableCell>
              <TableCell>{c.license}</TableCell>
              <TableCell>
                <a href={c.source} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                  link
                </a>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
